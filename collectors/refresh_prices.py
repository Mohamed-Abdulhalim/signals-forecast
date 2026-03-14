"""
collectors/refresh_prices.py

Lightweight 4-hour price refresher.
Only updates the current price in today's JSON files.
Does NOT regenerate signals or forecasts — those run weekly.

Sources used (fast, no Alpha Vantage quota consumed):
  - yfinance: Gold (GC=F), USD Index (DX-Y.NYB), Brent (BZ=F),
               Natural Gas (NG=F), Wheat (ZW=F), Corn (ZC=F)
  - metals.live: Gold fallback
  - Alpha Vantage: Rice fallback only (PDBA ETF)
"""

import requests
import json
import os
from datetime import datetime

DATA_DIR = 'data/prices'
TODAY    = datetime.now().strftime('%Y%m%d')
AV_KEY   = os.environ.get('ALPHA_VANTAGE_KEY', '')

# ── Fetch helpers ────────────────────────────────────────────────

def yf_price(ticker, low, high):
    """Fetch latest close from yfinance with sanity bounds."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period='2d')
        if not hist.empty:
            price = round(float(hist['Close'].iloc[-1]), 2)
            if low < price < high:
                return price
            print(f"  [WARN] {ticker} price {price} outside ({low},{high}) — rejected")
    except Exception as e:
        print(f"  [WARN] yfinance {ticker} failed: {e}")
    return None

def metals_live_gold():
    try:
        r = requests.get('https://api.metals.live/v1/spot/gold', timeout=10)
        if r.status_code == 200:
            price = float(r.json()[0]['price'])
            if 1500 < price < 5000:
                return price
    except Exception as e:
        print(f"  [WARN] metals.live failed: {e}")
    return None

def av_etf_price(symbol, low, high):
    """Alpha Vantage daily close — only used for Rice (PDBA)."""
    if not AV_KEY:
        return None
    try:
        url = (
            f'https://www.alphavantage.co/query'
            f'?function=TIME_SERIES_DAILY&symbol={symbol}'
            f'&apikey={AV_KEY}'
        )
        r = requests.get(url, timeout=15)
        series = r.json().get('Time Series (Daily)', {})
        if series:
            latest = sorted(series.keys())[-1]
            price = round(float(series[latest]['4. close']), 2)
            if low < price < high:
                return price
    except Exception as e:
        print(f"  [WARN] AV {symbol} failed: {e}")
    return None

# ── Price map ────────────────────────────────────────────────────
# Each entry: (category, asset_name, fetch_function)

def fetch_all_prices():
    print("Fetching current prices...\n")

    prices = {}

    # Energy
    brent = yf_price('BZ=F', 20, 200)
    if brent:
        prices[('energy', 'Brent Oil')] = brent
        print(f"  Brent Oil:   ${brent}")

    natgas = yf_price('NG=F', 0.5, 20)
    if natgas:
        prices[('energy', 'Natural Gas')] = natgas
        print(f"  Natural Gas: ${natgas}")

    # Safe Haven — Gold: metals.live first, then yfinance
    gold = yf_price('GC=F', 2500, 4000)
    if not gold:
        gld = yf_price('GLD', 240, 500)
        if gld:
            gold = round(gld * 6.5, 2)  # GLD ≈ spot/10 × 65% factor
            print(f"  Gold (via GLD scaled): ${gold}")
    if gold:
        prices[('safe_haven', 'Gold')] = gold
        print(f"  Gold:        ${gold}")

    # Safe Haven — USD Index: real DXY
    dxy = yf_price('DX=F', 80, 130) or yf_price('DX-Y.NYB', 80, 130)
    if dxy:
        prices[('safe_haven', 'USD Index')] = dxy
        print(f"  USD Index:   {dxy}")

    # Food
    wheat = yf_price('ZW=F', 100, 2000)
    if wheat:
        prices[('food', 'Wheat')] = wheat
        print(f"  Wheat:       ${wheat}")

    corn = yf_price('ZC=F', 100, 2000)
    if corn:
        prices[('food', 'Corn')] = corn
        print(f"  Corn:        ${corn}")

    # Rice: yfinance PDBA ETF, fallback to AV
    rice = yf_price('PDBA', 5, 200) or av_etf_price('PDBA', 5, 200)
    if rice:
        prices[('food', 'Rice')] = rice
        print(f"  Rice:        ${rice}")

    return prices

# ── Update today's files ─────────────────────────────────────────

def update_today_files(prices):
    """
    For each category, load today's file if it exists and update
    the price field for each matching asset. If today's file doesn't
    exist yet, create it from scratch.
    """
    # Group by category
    by_category = {}
    for (category, asset), price in prices.items():
        by_category.setdefault(category, {})[asset] = price

    updated = 0
    for category, asset_prices in by_category.items():
        filepath = f"{DATA_DIR}/{category}_{TODAY}.json"

        if os.path.exists(filepath):
            with open(filepath) as f:
                data = json.load(f)

            for asset in data.get('assets', []):
                if asset['asset'] in asset_prices:
                    old = asset['price']
                    asset['prev_price'] = old          # ← store previous price
                    asset['price'] = asset_prices[asset['asset']]
                    asset['timestamp'] = datetime.now().isoformat()
                    print(f"  Updated {asset['asset']}: ${old} → ${asset['price']}")

            data['timestamp'] = datetime.now().isoformat()

        else:
            # Today's file doesn't exist yet — create it
            data = {
                'category':  category,
                'timestamp': datetime.now().isoformat(),
                'assets': [
                    {
                        'asset':     asset_name,
                        'price':     price,
                        'date':      datetime.now().strftime('%Y-%m-%d'),
                        'timestamp': datetime.now().isoformat()
                    }
                    for asset_name, price in asset_prices.items()
                ]
            }
            print(f"  Created new file for {category} (daily collector hasn't run yet today)")

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        updated += 1

    return updated

# ── Main ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)

    prices  = fetch_all_prices()
    updated = update_today_files(prices)

    print(f"\nDone. Updated {len(prices)} prices across {updated} files.")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
