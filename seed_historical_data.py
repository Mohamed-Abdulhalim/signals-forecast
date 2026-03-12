"""
seed_historical_data.py v3

Run ONCE via GitHub Actions to backfill 6 months of historical price data.

Sources:
  Alpha Vantage → Brent Oil, Natural Gas, Wheat, Corn  (commodity endpoints)
  Stooq CSV     → Gold, USD Index, Rice                (free, no API key)

Stooq URLs return CSV directly — no auth, works from GitHub Actions.
"""

import json
import os
import time
import csv
import io
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv('ALPHA_VANTAGE_KEY')
DATA_DIR = 'data/prices'
DAYS_BACK = 180

os.makedirs(DATA_DIR, exist_ok=True)

# ── Asset definitions ────────────────────────────────────────

ASSETS = [
    # Alpha Vantage commodity endpoints
    {'category': 'energy',     'asset': 'Brent Oil',  'symbol': 'BRENT',  'source': 'av_commodity', 'key': 'BRENT'},
    {'category': 'energy',     'asset': 'Natural Gas', 'symbol': 'NATGAS', 'source': 'av_commodity', 'key': 'NATURAL_GAS'},
    {'category': 'food',       'asset': 'Wheat',       'symbol': 'WHEAT',  'source': 'av_commodity', 'key': 'WHEAT'},
    {'category': 'food',       'asset': 'Corn',        'symbol': 'CORN',   'source': 'av_commodity', 'key': 'CORN'},

    # Stooq CSV — free, no API key, works from cloud servers
    # GC.F = Gold futures, DX.F = USD Index futures, RR.F = Rough Rice futures
    {'category': 'safe_haven', 'asset': 'Gold',        'symbol': 'XAU',    'source': 'stooq', 'key': 'gc.f'},
    {'category': 'safe_haven', 'asset': 'USD Index',   'symbol': 'DXY',    'source': 'stooq', 'key': 'dx.f'},
    {'category': 'food',       'asset': 'Rice',        'symbol': 'RICE',   'source': 'stooq', 'key': 'rr.f'},
]

# ── Fetchers ─────────────────────────────────────────────────

def fetch_av_commodity(function_name):
    """Alpha Vantage commodity endpoint → {date: price}"""
    url = 'https://www.alphavantage.co/query'
    params = {'function': function_name, 'interval': 'daily', 'apikey': API_KEY}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        if 'data' not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] {function_name}: {msg[:120]}")
            return {}
        result = {}
        for entry in data['data']:
            try:
                val = entry['value']
                if val in ('.', None, ''):
                    continue
                result[entry['date']] = round(float(val), 4)
            except (ValueError, KeyError):
                continue
        print(f"    [OK] {function_name}: {len(result)} points")
        return result
    except Exception as e:
        print(f"    [ERROR] {function_name}: {e}")
        return {}


def fetch_stooq(symbol):
    """
    Stooq historical CSV → {date: close_price}
    URL format: https://stooq.com/q/d/l/?s=SYMBOL&i=d
    Returns daily data, no API key needed.
    """
    url = f'https://stooq.com/q/d/l/?s={symbol}&i=d'
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; market-data-collector/1.0)'
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"    [WARN] Stooq {symbol}: HTTP {r.status_code}")
            return {}

        content = r.text.strip()
        if not content or 'No data' in content or len(content) < 50:
            print(f"    [WARN] Stooq {symbol}: empty or no data response")
            return {}

        result = {}
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            try:
                date_str = row.get('Date', '').strip()
                close    = row.get('Close', '').strip()
                if not date_str or not close:
                    continue
                result[date_str] = round(float(close), 4)
            except (ValueError, KeyError):
                continue

        print(f"    [OK] Stooq {symbol}: {len(result)} points")
        return result

    except Exception as e:
        print(f"    [ERROR] Stooq {symbol}: {e}")
        return {}


# ── File helpers ─────────────────────────────────────────────

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

# ── Writer ───────────────────────────────────────────────────

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
                alt = (dt_obj + timedelta(days=d)).strftime('%Y-%m-%d')
                price = history.get(alt)
                if price:
                    break
        if price is None:
            continue

        filepath = os.path.join(DATA_DIR, f"{category}_{file_date}.json")
        existing = load_file(filepath) or {
            'category': category,
            'timestamp': dt_obj.isoformat(),
            'assets': []
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

# ── Main ─────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("[FATAL] ALPHA_VANTAGE_KEY not set.")
        return

    print("=" * 57)
    print("  Signals & Forecasts — Historical Seeder v3")
    print(f"  {DAYS_BACK} days | AV commodity + Stooq CSV")
    print("=" * 57)

    dates         = date_range(DAYS_BACK)
    total_written = 0

    for a in ASSETS:
        print(f"\n[{a['category'].upper()}] {a['asset']} ...")

        if a['source'] == 'av_commodity':
            history = fetch_av_commodity(a['key'])
            # Polite delay for Alpha Vantage rate limit (5 req/min free tier)
            time.sleep(13)
        elif a['source'] == 'stooq':
            history = fetch_stooq(a['key'])
            time.sleep(2)   # Stooq is more lenient
        else:
            print("    [SKIP] Unknown source.")
            continue

        if not history:
            print("    No data — skipped.")
            continue

        written        = write_to_daily_files(
            a['category'], a['asset'], a['symbol'], history, dates)
        total_written += written
        print(f"    Written to {written} daily files.")

    print("\n" + "=" * 57)
    print(f"  Done. {total_written} asset-day records written.")
    print(f"  {os.path.abspath(DATA_DIR)}")
    print("=" * 57)
    print("\nNext:  python analysis/signals.py")
    print("       python analysis/forecasts.py")

if __name__ == '__main__':
    main()
