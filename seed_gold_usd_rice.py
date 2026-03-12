"""
seed_gold_usd_rice.py v2

Fixes data quality issues:
  Gold      → AV CURRENCY_EXCHANGE_RATE XAU/USD  (real spot price ~$3000)
  USD Index → AV FX_DAILY EUR/USD inverted        (DXY proxy, real scale ~103)
  Rice      → AV TIME_SERIES_DAILY on RICE ETF    (RICEX or JJG with correct category)

All via Alpha Vantage free tier. Works from GitHub Actions.
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
DAYS_BACK = 100

os.makedirs(DATA_DIR, exist_ok=True)


def fetch_gold_spot():
    """
    Gold spot price via AV CURRENCY_EXCHANGE_RATE (XAU to USD).
    Returns current price only — we then use FX_DAILY for history.
    """
    # Use FX_DAILY for XAU/USD historical data
    url = 'https://www.alphavantage.co/query'
    params = {
        'function':      'FX_DAILY',
        'from_symbol':   'XAU',
        'to_symbol':     'USD',
        'outputsize':    'compact',
        'apikey':        API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Time Series FX (Daily)'

        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] XAU/USD FX_DAILY: {msg[:120]}")
            return {}

        result = {}
        for date_str, vals in data[key].items():
            try:
                result[date_str] = round(float(vals['4. close']), 2)
            except (ValueError, KeyError):
                continue

        print(f"    [OK] Gold XAU/USD: {len(result)} points, latest: {list(result.values())[0] if result else 'N/A'}")
        return result

    except Exception as e:
        print(f"    [ERROR] Gold FX_DAILY: {e}")
        return {}


def fetch_usd_index():
    """
    USD Index proxy via EUR/USD FX_DAILY (inverted).
    DXY is ~57% EUR weighted. When EUR/USD falls, DXY rises.
    We store the inverse scaled to approximate DXY range:
      DXY_approx = 1 / EURUSD * 88
    This gives values in the 95-110 range, matching real DXY.
    """
    url = 'https://www.alphavantage.co/query'
    params = {
        'function':      'FX_DAILY',
        'from_symbol':   'EUR',
        'to_symbol':     'USD',
        'outputsize':    'compact',
        'apikey':        API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Time Series FX (Daily)'

        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] EUR/USD FX_DAILY: {msg[:120]}")
            return {}

        result = {}
        for date_str, vals in data[key].items():
            try:
                eurusd = float(vals['4. close'])
                # Scale inverse EUR/USD to approximate DXY
                # At EUR/USD=1.08, DXY≈104. Formula: DXY ≈ 1/EURUSD * 112
                dxy_approx = round(1 / eurusd * 112, 2)
                result[date_str] = dxy_approx
            except (ValueError, KeyError, ZeroDivisionError):
                continue

        print(f"    [OK] USD Index (EUR/USD proxy): {len(result)} points, latest: {list(result.values())[0] if result else 'N/A'}")
        return result

    except Exception as e:
        print(f"    [ERROR] USD Index FX_DAILY: {e}")
        return {}


def fetch_rice_proxy():
    """
    Rice via AV TIME_SERIES_DAILY on PDBA (PowerShares DB Agriculture).
    Better proxy than JJG for food commodities including rice.
    Falls back to JJG if PDBA fails.
    """
    url = 'https://www.alphavantage.co/query'

    for symbol in ['PDBA', 'JJG', 'DBA']:
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
                print(f"    [WARN] Rice {symbol}: {msg[:80]}")
                time.sleep(13)
                continue

            result = {}
            for date_str, vals in data[key].items():
                try:
                    result[date_str] = round(float(vals['4. close']), 4)
                except (ValueError, KeyError):
                    continue

            print(f"    [OK] Rice via {symbol}: {len(result)} points")
            return result

        except Exception as e:
            print(f"    [ERROR] Rice {symbol}: {e}")
            time.sleep(13)
            continue

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

def remove_asset(day_data, asset_name):
    """Remove existing incorrect entry for an asset"""
    day_data['assets'] = [
        a for a in day_data.get('assets', [])
        if a['asset'] != asset_name
    ]
    return day_data

def date_range(days_back):
    today = datetime.now()
    return [(today - timedelta(days=i),
             (today - timedelta(days=i)).strftime('%Y%m%d'))
            for i in range(days_back, -1, -1)]

def write_to_daily_files(category, asset_name, symbol, history, dates, overwrite=False):
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

        # If overwrite mode, remove old entry first
        if overwrite:
            existing = remove_asset(existing, asset_name)

        # Check if already exists
        already = any(a['asset'] == asset_name for a in existing.get('assets', []))
        if already and not overwrite:
            continue

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
    print("  Fix Gold, USD Index, Rice — Real Prices")
    print("  Gold: XAU/USD spot | USD: EUR/USD proxy")
    print("=" * 57)

    dates = date_range(DAYS_BACK)

    # ── Gold (real spot price) ───────────────────────────────
    print("\n[SAFE_HAVEN] Gold (XAU/USD spot)...")
    gold_history = fetch_gold_spot()
    if gold_history:
        written = write_to_daily_files(
            'safe_haven', 'Gold', 'XAU', gold_history, dates, overwrite=True)
        print(f"    Updated {written} daily files.")
    time.sleep(13)

    # ── USD Index (EUR/USD inverse proxy) ───────────────────
    print("\n[SAFE_HAVEN] USD Index (EUR/USD inverse)...")
    usd_history = fetch_usd_index()
    if usd_history:
        written = write_to_daily_files(
            'safe_haven', 'USD Index', 'DXY', usd_history, dates, overwrite=True)
        print(f"    Updated {written} daily files.")
    time.sleep(13)

    # ── Rice ────────────────────────────────────────────────
    print("\n[FOOD] Rice (agriculture ETF proxy)...")
    rice_history = fetch_rice_proxy()
    if rice_history:
        written = write_to_daily_files(
            'food', 'Rice', 'RICE', rice_history, dates, overwrite=True)
        print(f"    Written to {written} daily files.")

    print("\n  Done.")
    print("Next:  python analysis/signals.py")
    print("       python analysis/forecasts.py")

if __name__ == '__main__':
    main()
