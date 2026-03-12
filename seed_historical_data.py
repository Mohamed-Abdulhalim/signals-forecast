"""
seed_historical_data.py v2

Run ONCE via GitHub Actions to backfill 6 months of historical price data.
Uses Alpha Vantage for ALL assets — reliable from GitHub Actions servers.
Free tier uses 7 API calls total — well within the 25/day limit.

Assets:
  Energy:     Brent Oil, Natural Gas      (AV commodity endpoints)
  Safe Haven: Gold (GLD ETF), USD Index (UUP ETF)
  Food:       Wheat, Corn, Rice           (AV commodity endpoints)
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
DAYS_BACK = 180

os.makedirs(DATA_DIR, exist_ok=True)

# ── Asset definitions ────────────────────────────────────────
# type 'commodity' → AV BRENT/NATURAL_GAS/WHEAT/CORN/RICE endpoint
# type 'etf'       → AV TIME_SERIES_DAILY on a proxy ETF

ASSETS = [
    {'category': 'energy',     'asset': 'Brent Oil',   'symbol': 'BRENT',  'av_fn': 'BRENT',        'type': 'commodity'},
    {'category': 'energy',     'asset': 'Natural Gas',  'symbol': 'NATGAS', 'av_fn': 'NATURAL_GAS',  'type': 'commodity'},
    {'category': 'safe_haven', 'asset': 'Gold',         'symbol': 'XAU',    'av_fn': 'GLD',          'type': 'etf'},
    {'category': 'safe_haven', 'asset': 'USD Index',    'symbol': 'DXY',    'av_fn': 'UUP',          'type': 'etf'},
    {'category': 'food',       'asset': 'Wheat',        'symbol': 'WHEAT',  'av_fn': 'WHEAT',        'type': 'commodity'},
    {'category': 'food',       'asset': 'Corn',         'symbol': 'CORN',   'av_fn': 'CORN',         'type': 'commodity'},
    {'category': 'food',       'asset': 'Rice',         'symbol': 'RICE',   'av_fn': 'RICE',         'type': 'commodity'},
]

# ── Fetchers ─────────────────────────────────────────────────

def fetch_commodity(function_name):
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


def fetch_etf(symbol):
    """Alpha Vantage TIME_SERIES_DAILY → {date: close_price}"""
    url = 'https://www.alphavantage.co/query'
    params = {'function': 'TIME_SERIES_DAILY', 'symbol': symbol,
              'outputsize': 'full', 'apikey': API_KEY}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        key = 'Time Series (Daily)'
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
        print(f"    [OK] {symbol} ETF: {len(result)} points")
        return result
    except Exception as e:
        print(f"    [ERROR] ETF {symbol}: {e}")
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
        if dt_obj.weekday() >= 5:       # skip weekends
            continue
        cal_date = dt_obj.strftime('%Y-%m-%d')
        if cal_date < cutoff:
            continue

        price = history.get(cal_date)
        if price is None:               # try adjacent days for holidays
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

    print("=" * 55)
    print("  Signals & Forecasts — Historical Seeder v2")
    print(f"  {DAYS_BACK} days back | All via Alpha Vantage")
    print("=" * 55)

    dates         = date_range(DAYS_BACK)
    total_written = 0

    for a in ASSETS:
        print(f"\n[{a['category'].upper()}] {a['asset']} ...")

        history = (fetch_commodity(a['av_fn'])
                   if a['type'] == 'commodity'
                   else fetch_etf(a['av_fn']))

        if not history:
            print("    No data — skipped.")
            time.sleep(13)
            continue

        written        = write_to_daily_files(
            a['category'], a['asset'], a['symbol'], history, dates)
        total_written += written
        print(f"    Written to {written} daily files.")

        # Free tier: 25 req/day, ~5 req/min → wait 13s between calls
        time.sleep(13)

    print("\n" + "=" * 55)
    print(f"  Done. {total_written} asset-day records written.")
    print(f"  {os.path.abspath(DATA_DIR)}")
    print("=" * 55)
    print("\nNext:  python analysis/signals.py")
    print("       python analysis/forecasts.py")

if __name__ == '__main__':
    main()
