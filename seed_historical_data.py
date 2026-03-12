"""
seed_historical_data.py

Run this ONCE to backfill 6 months of historical price data for all 7 assets.
This creates daily JSON files in data/prices/ in the exact format the system expects,
so signals.py and forecasts.py work immediately without any changes.

Usage:
    python seed_historical_data.py

Requirements:
    pip install yfinance requests python-dotenv
"""

import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
from dotenv import load_dotenv
import requests

load_dotenv()

DATA_DIR = 'data/prices'
os.makedirs(DATA_DIR, exist_ok=True)

DAYS_BACK = 180  # 6 months

# ─────────────────────────────────────────────
# Asset definitions
# ─────────────────────────────────────────────

YFINANCE_ASSETS = {
    'safe_haven': [
        {'ticker': 'GC=F',    'asset': 'Gold',      'symbol': 'XAU'},
        {'ticker': 'DX-Y.NYB','asset': 'USD Index',  'symbol': 'DXY'},
    ],
    'food': [
        {'ticker': 'ZW=F', 'asset': 'Wheat', 'symbol': 'ZW'},
        {'ticker': 'ZC=F', 'asset': 'Corn',  'symbol': 'ZC'},
        {'ticker': 'ZR=F', 'asset': 'Rice',  'symbol': 'ZR'},
    ],
    'energy': [
        {'ticker': 'NG=F', 'asset': 'Natural Gas', 'symbol': 'NATGAS'},
    ],
}

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def date_range(days_back):
    """Return list of (datetime, str) tuples from oldest to today."""
    today = datetime.now()
    return [(today - timedelta(days=i), (today - timedelta(days=i)).strftime('%Y%m%d'))
            for i in range(days_back, -1, -1)]


def load_existing(filepath):
    """Load an existing daily file or return a blank template."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def save_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def asset_already_exists(day_data, asset_name):
    return any(a['asset'] == asset_name for a in day_data.get('assets', []))


# ─────────────────────────────────────────────
# yfinance bulk fetch
# ─────────────────────────────────────────────

def fetch_yfinance_history(ticker_symbol, days_back):
    """
    Returns a dict of {date_str: close_price} for the past N days.
    date_str format: 'YYYY-MM-DD'
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=f'{days_back}d')
        if hist.empty:
            print(f"  [WARN] No yfinance data for {ticker_symbol}")
            return {}
        result = {}
        for idx, row in hist.iterrows():
            date_str = idx.strftime('%Y-%m-%d')
            result[date_str] = round(float(row['Close']), 4)
        return result
    except Exception as e:
        print(f"  [ERROR] yfinance {ticker_symbol}: {e}")
        return {}


# ─────────────────────────────────────────────
# Alpha Vantage Brent Oil fetch
# ─────────────────────────────────────────────

def fetch_brent_history():
    """
    Fetches full Brent Oil daily series from Alpha Vantage.
    Returns dict of {date_str: price}.
    """
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    if not api_key:
        print("  [WARN] No ALPHA_VANTAGE_KEY found — skipping Brent Oil history.")
        return {}

    url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'BRENT',
        'interval': 'daily',
        'apikey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if 'data' not in data:
            print(f"  [WARN] Alpha Vantage Brent response unexpected: {list(data.keys())}")
            return {}

        result = {}
        for entry in data['data']:
            try:
                val = float(entry['value'])
                result[entry['date']] = round(val, 4)
            except (ValueError, KeyError):
                continue

        print(f"  [OK] Brent Oil: {len(result)} data points from Alpha Vantage")
        return result

    except Exception as e:
        print(f"  [ERROR] Brent Oil Alpha Vantage: {e}")
        return {}


# ─────────────────────────────────────────────
# Write data into daily files
# ─────────────────────────────────────────────

def write_asset_to_daily_files(category, asset_def, price_history, dates):
    """
    For each date in `dates`, if price_history has a price for that date,
    write/update the daily category JSON file.
    """
    asset_name = asset_def['asset']
    symbol = asset_def['symbol']
    written = 0

    for dt_obj, file_date_str in dates:
        calendar_date = dt_obj.strftime('%Y-%m-%d')

        # Skip weekends — markets closed, no data expected
        if dt_obj.weekday() >= 5:
            continue

        price = price_history.get(calendar_date)
        if price is None:
            # Try adjacent days (sometimes data is lagged by 1 day)
            for delta in [-1, 1, -2]:
                alt_date = (dt_obj + timedelta(days=delta)).strftime('%Y-%m-%d')
                price = price_history.get(alt_date)
                if price:
                    break

        if price is None:
            continue

        filepath = os.path.join(DATA_DIR, f"{category}_{file_date_str}.json")
        existing = load_existing(filepath)

        if existing is None:
            existing = {
                'category': category,
                'timestamp': dt_obj.isoformat(),
                'assets': []
            }

        if not asset_already_exists(existing, asset_name):
            existing['assets'].append({
                'asset': asset_name,
                'symbol': symbol,
                'price': price,
                'date': calendar_date,
                'timestamp': dt_obj.isoformat()
            })
            save_file(filepath, existing)
            written += 1

    return written


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Signals & Forecasts — Historical Data Seeder")
    print(f"  Seeding {DAYS_BACK} days back from today")
    print("=" * 55)

    dates = date_range(DAYS_BACK)
    total_written = 0

    # ── 1. yfinance assets ──────────────────────────────
    for category, assets in YFINANCE_ASSETS.items():
        for asset_def in assets:
            ticker = asset_def['ticker']
            name = asset_def['asset']
            print(f"\n[{category.upper()}] Fetching {name} ({ticker})...")
            history = fetch_yfinance_history(ticker, DAYS_BACK + 10)

            if not history:
                print(f"  Skipped — no data returned.")
                continue

            written = write_asset_to_daily_files(category, asset_def, history, dates)
            total_written += written
            print(f"  Written to {written} daily files.")
            time.sleep(0.5)  # polite delay

    # ── 2. Brent Oil via Alpha Vantage ──────────────────
    print(f"\n[ENERGY] Fetching Brent Oil (Alpha Vantage)...")
    brent_history = fetch_brent_history()
    if brent_history:
        brent_def = {'asset': 'Brent Oil', 'symbol': 'BRENT'}
        written = write_asset_to_daily_files('energy', brent_def, brent_history, dates)
        total_written += written
        print(f"  Written to {written} daily files.")

    # ── 3. Summary ──────────────────────────────────────
    print("\n" + "=" * 55)
    print(f"  Done. {total_written} asset-day records written.")
    print(f"  Files saved to: {os.path.abspath(DATA_DIR)}")
    print("=" * 55)
    print("\nNext steps:")
    print("  python analysis/signals.py")
    print("  python analysis/forecasts.py")
    print("  python web/app.py")


if __name__ == '__main__':
    main()
