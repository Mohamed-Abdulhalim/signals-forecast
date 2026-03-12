"""
seed_gold_usd_rice.py v3

Gold: Uses AV CURRENCY_EXCHANGE_RATE to get real spot price,
      then scales GLD historical data to match spot price ratio.
      e.g. if spot=3000 and GLD=276, scale_factor=10.87
      All historical GLD prices multiplied by scale_factor → real gold prices

USD Index: EUR/USD inverse proxy (working fine, keep as is)
Rice: PDBA ETF proxy (working fine, keep as is)

Also fixes the inverted bounds bug in gold forecasts.
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


def fetch_gold_spot_price():
    """Get current XAU/USD spot price via AV CURRENCY_EXCHANGE_RATE"""
    url = 'https://www.alphavantage.co/query'
    params = {
        'function':       'CURRENCY_EXCHANGE_RATE',
        'from_currency':  'XAU',
        'to_currency':    'USD',
        'apikey':         API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Realtime Currency Exchange Rate'
        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] XAU spot: {msg[:120]}")
            return None
        price = float(data[key]['5. Exchange Rate'])
        print(f"    [OK] Gold spot price: ${price:,.2f}")
        return price
    except Exception as e:
        print(f"    [ERROR] Gold spot: {e}")
        return None


def fetch_gld_etf_history():
    """Get GLD ETF history to use as price shape"""
    url = 'https://www.alphavantage.co/query'
    params = {
        'function':   'TIME_SERIES_DAILY',
        'symbol':     'GLD',
        'outputsize': 'compact',
        'apikey':     API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Time Series (Daily)'
        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] GLD history: {msg[:120]}")
            return {}
        result = {}
        for date_str, vals in data[key].items():
            try:
                result[date_str] = float(vals['4. close'])
            except (ValueError, KeyError):
                continue
        print(f"    [OK] GLD history: {len(result)} points")
        return result
    except Exception as e:
        print(f"    [ERROR] GLD history: {e}")
        return {}


def scale_gld_to_gold(gld_history, spot_price):
    """
    Scale GLD ETF prices to real gold spot prices.
    GLD tracks gold at roughly 1/10th of spot price.
    We calculate exact ratio from today's data.
    """
    if not gld_history or not spot_price:
        return {}

    # Get most recent GLD price
    most_recent_gld = list(gld_history.values())[0]
    scale_factor    = spot_price / most_recent_gld

    print(f"    Scale factor: {scale_factor:.4f} (GLD ${most_recent_gld} → Gold ${spot_price:,.2f})")

    scaled = {}
    for date_str, gld_price in gld_history.items():
        scaled[date_str] = round(gld_price * scale_factor, 2)

    return scaled


def fetch_usd_index():
    """EUR/USD inverse proxy for DXY — already working"""
    url = 'https://www.alphavantage.co/query'
    params = {
        'function':    'FX_DAILY',
        'from_symbol': 'EUR',
        'to_symbol':   'USD',
        'outputsize':  'compact',
        'apikey':      API_KEY,
    }
    try:
        r    = requests.get(url, params=params, timeout=20)
        data = r.json()
        key  = 'Time Series FX (Daily)'
        if key not in data:
            msg = data.get('Note') or data.get('Information') or str(list(data.keys()))
            print(f"    [WARN] EUR/USD: {msg[:120]}")
            return {}
        result = {}
        for date_str, vals in data[key].items():
            try:
                eurusd         = float(vals['4. close'])
                result[date_str] = round(1 / eurusd * 112, 2)
            except (ValueError, KeyError, ZeroDivisionError):
                continue
        print(f"    [OK] USD Index: {len(result)} points, latest: {list(result.values())[0] if result else 'N/A'}")
        return result
    except Exception as e:
        print(f"    [ERROR] USD Index: {e}")
        return {}


def fetch_rice():
    """PDBA agriculture ETF proxy — already working"""
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

        if overwrite:
            existing = remove_asset(existing, asset_name)

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
    print("  Fix Gold, USD Index, Rice — Real Prices v3")
    print("=" * 57)

    dates = date_range(DAYS_BACK)

    # ── Gold ────────────────────────────────────────────────
    print("\n[SAFE_HAVEN] Gold (scaled to real spot price)...")
    spot_price  = fetch_gold_spot_price()
    time.sleep(13)
    gld_history = fetch_gld_etf_history()
    time.sleep(13)

    if spot_price and gld_history:
        gold_history = scale_gld_to_gold(gld_history, spot_price)
        written      = write_to_daily_files(
            'safe_haven', 'Gold', 'XAU', gold_history, dates, overwrite=True)
        print(f"    Updated {written} daily files with real gold prices.")
    else:
        print("    Could not get gold data — skipped.")

    # ── USD Index ───────────────────────────────────────────
    print("\n[SAFE_HAVEN] USD Index (EUR/USD inverse)...")
    usd_history = fetch_usd_index()
    time.sleep(13)
    if usd_history:
        written = write_to_daily_files(
            'safe_haven', 'USD Index', 'DXY', usd_history, dates, overwrite=True)
        print(f"    Updated {written} daily files.")

    # ── Rice ────────────────────────────────────────────────
    print("\n[FOOD] Rice (agriculture ETF)...")
    rice_history = fetch_rice()
    if rice_history:
        written = write_to_daily_files(
            'food', 'Rice', 'RICE', rice_history, dates, overwrite=True)
        print(f"    Updated {written} daily files.")

    print("\n  Done.")
    print("Next:  python analysis/signals.py")
    print("       python analysis/forecasts.py")

if __name__ == '__main__':
    main()
