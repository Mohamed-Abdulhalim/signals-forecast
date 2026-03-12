"""
seed_gold_usd_rice.py

Adds Gold, USD Index, and Rice to existing daily files.
Uses Alpha Vantage TIME_SERIES_DAILY with outputsize=compact (last 100 days).
This is free tier compatible and works reliably from GitHub Actions.

Proxies used:
  Gold      → GLD  (SPDR Gold ETF, tracks spot gold closely)
  USD Index → UUP  (Invesco DB USD Bull ETF, tracks DXY)
  Rice      → JJG  (iPath Bloomberg Grains ETF, best free proxy for rice)

Run this ONCE from GitHub Actions after the main seed has completed.
"""

import json
import os
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv('ALPHA_VANTAGE_KEY')
DATA_DIR = 'data/prices'
DAYS_BACK = 100  # compact mode gives last 100 trading days

os.makedirs(DATA_DIR, exist_ok=True)

ASSETS = [
    {'category': 'safe_haven', 'asset': 'Gold',      'symbol': 'XAU',  'av_symbol': 'GLD'},
    {'category': 'safe_haven', 'asset': 'USD Index',  'symbol': 'DXY',  'av_symbol': 'UUP'},
    {'category': 'food',       'asset': 'Rice',       'symbol': 'RICE', 'av_symbol': 'JJG'},
]

def fetch_av_compact(symbol):
    url    = 'https://www.alphavantage.co/query'
    params = {
        'function':   'TIME_SERIES_DAILY',
        'symbol':     symbol,
        'outputsize': 'compact',
        'apikey':     API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Time Series (Daily)'

        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] {symbol}: {msg[:120]}")
            return {}

        result = {}
        for date_str, vals in data[key].items():
            try:
                result[date_str] = round(float(vals['4. close']), 4)
            except (ValueError, KeyError):
                continue

        print(f"    [OK] {symbol}: {len(result)} points")
        return result

    except Exception as e:
        print(f"    [ERROR] {symbol}: {e}")
        return {}

def load_file(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def save_file(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def already_has(day_data, asset_name):
    return any(a['asset'] == asset_name for a in day_data.get('assets', []))

def date_range(days_back):
    today = datetime.now()
    return [(today - timedelta(days=i),
             (today - timedelta(days=i)).strftime('%Y%m%d'))
            for i in range(days_back, -1, -1)]

def write_to_daily_files(category, asset_name, symbol, history, dates):
    written = 0
    cutoff  = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')

    for dt_obj, file_date in dates:
        if dt_obj.weekday() >= 5:
            continue
        cal_date = dt_obj.strftime('%Y-%m-%d')
        if cal_date < cutoff:
            continue

        price = history.get(cal_date)
        if price is None:
            for d in [-1, 1, -2, 2]:
                alt   = (dt_obj + timedelta(days=d)).strftime('%Y-%m-%d')
                price = history.get(alt)
                if price:
                    break
        if price is None:
            continue

        filepath = os.path.join(DATA_DIR, f"{category}_{file_date}.json")
        existing = load_file(filepath) or {
            'category':  category,
            'timestamp': dt_obj.isoformat(),
            'assets':    []
        }

        if not already_has(existing, asset_name):
            existing['assets'].append({
                'asset':     asset_name,
                'symbol':    symbol,
                'price':     price,
                'date':      cal_date,
                'timestamp': dt_obj.isoformat()
            })
            save_file(filepath, existing)
            written += 1

    return written

def main():
    if not API_KEY:
        print("[FATAL] ALPHA_VANTAGE_KEY not set.")
        return

    print("=" * 55)
    print("  Seeding Gold, USD Index, Rice")
    print("  Source: Alpha Vantage compact (100 days)")
    print("=" * 55)

    dates         = date_range(DAYS_BACK)
    total_written = 0

    for a in ASSETS:
        print(f"\n[{a['category'].upper()}] {a['asset']} via {a['av_symbol']}...")
        history = fetch_av_compact(a['av_symbol'])

        if not history:
            print("    No data — skipped.")
            time.sleep(13)
            continue

        written        = write_to_daily_files(
            a['category'], a['asset'], a['symbol'], history, dates)
        total_written += written
        print(f"    Written to {written} daily files.")
        time.sleep(13)  # AV free tier: 5 requests/min

    print(f"\n  Done. {total_written} records written.")
    print("\nNext:  python analysis/signals.py")
    print("       python analysis/forecasts.py")

if __name__ == '__main__':
    main()
