"""
seed_wheat_corn.py

One-time backfill of 180 days of Wheat and Corn daily price data
using yfinance futures tickers:
  ZW=F → Chicago Wheat futures (cents/bushel → divide by 100 for $/bushel)
  ZC=F → Chicago Corn futures (cents/bushel → divide by 100 for $/bushel)

Run via GitHub Actions workflow: seed_wheat_corn.yml
"""

import json
import os
from datetime import datetime, timedelta
import yfinance as yf

DATA_DIR  = 'data/prices'
DAYS_BACK = 180

os.makedirs(DATA_DIR, exist_ok=True)

ASSETS = [
    {'asset': 'Wheat', 'symbol': 'WHEAT', 'ticker': 'ZW=F', 'category': 'food', 'scale': 1.0},
    {'asset': 'Corn',  'symbol': 'CORN',  'ticker': 'ZC=F', 'category': 'food', 'scale': 1.0},
]


def fetch_yfinance_history(ticker, days_back):
    """Fetch daily OHLCV history from yfinance → {date: close_price}"""
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period=f'{days_back}d', interval='1d')
        if hist.empty:
            print(f"    [WARN] {ticker}: empty response")
            return {}
        result = {}
        for idx, row in hist.iterrows():
            date_str = idx.strftime('%Y-%m-%d')
            price    = round(float(row['Close']), 4)
            if price > 0:
                result[date_str] = price
        print(f"    [OK] {ticker}: {len(result)} points, latest: {list(result.values())[-1] if result else 'N/A'}")
        return result
    except Exception as e:
        print(f"    [ERROR] {ticker}: {e}")
        return {}


def load_file(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_file(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def write_to_daily_files(category, asset_name, symbol, history, overwrite=False):
    written = 0
    cutoff  = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
    today   = datetime.now().strftime('%Y-%m-%d')

    for date_str, price in sorted(history.items()):
        if date_str < cutoff or date_str > today:
            continue

        # Convert date to file format YYYYMMDD
        file_date = date_str.replace('-', '')
        filepath  = os.path.join(DATA_DIR, f"{category}_{file_date}.json")

        existing = load_file(filepath) or {
            'category':  category,
            'timestamp': date_str + 'T00:00:00',
            'assets':    []
        }

        # Check if asset already exists
        already = any(a['asset'] == asset_name for a in existing.get('assets', []))

        if already and not overwrite:
            continue

        if already and overwrite:
            existing['assets'] = [a for a in existing['assets'] if a['asset'] != asset_name]

        existing['assets'].append({
            'asset':     asset_name,
            'symbol':    symbol,
            'price':     price,
            'date':      date_str,
            'timestamp': date_str + 'T00:00:00'
        })

        save_file(filepath, existing)
        written += 1

    return written


def main():
    print("=" * 57)
    print("  EdgePulse — Wheat & Corn Historical Seeder")
    print(f"  {DAYS_BACK} days | yfinance ZW=F + ZC=F")
    print("=" * 57)

    total = 0

    for a in ASSETS:
        print(f"\n[{a['category'].upper()}] {a['asset']} ({a['ticker']})...")
        history = fetch_yfinance_history(a['ticker'], DAYS_BACK)

        if not history:
            print(f"    No data — skipped.")
            continue

        written = write_to_daily_files(
            a['category'], a['asset'], a['symbol'], history, overwrite=True)
        total  += written
        print(f"    Written to {written} daily files.")

    print(f"\n  Done. {total} total records written.")
    print("\nNext:  python analysis/signals.py")
    print("       python analysis/forecasts.py")


if __name__ == '__main__':
    main()
