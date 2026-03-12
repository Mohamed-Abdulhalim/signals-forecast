"""
evaluate_predictions.py
Runs daily via GitHub Actions.
Checks if any prediction outcome windows have closed,
fetches actual prices, marks hits/misses, updates track_record.json.
"""

import json
import os
from datetime import date, datetime
import yfinance as yf

TICKERS = {
    'Brent Oil':   'BZ=F',
    'Natural Gas': 'NG=F',
    'Gold':        'GC=F',
    'USD Index':   'DX-Y.NYB',
    'Rice':        'PDBA',
    'Wheat':       'ZW=F',
    'Corn':        'ZC=F',
}

TRACK_FILE = 'data/track_record.json'

def fetch_price(asset):
    ticker = TICKERS.get(asset)
    if not ticker:
        return None
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='2d')
        if not hist.empty:
            return round(float(hist['Close'].iloc[-1]), 2)
    except Exception as e:
        print(f"  Error fetching {asset}: {e}")
    return None

def evaluate():
    if not os.path.exists(TRACK_FILE):
        print("No track record file found.")
        return

    with open(TRACK_FILE, 'r') as f:
        data = json.load(f)

    today = date.today().isoformat()
    changed = False

    for p in data['predictions']:
        if p['status'] != 'pending':
            continue

        if p['outcome_date'] > today:
            print(f"  {p['asset']}: outcome window still open (closes {p['outcome_date']})")
            continue

        print(f"  {p['asset']}: outcome window closed — fetching actual price...")
        actual = fetch_price(p['asset'])

        if actual is None:
            print(f"  {p['asset']}: could not fetch price, skipping")
            continue

        f30 = p['forecast_30_days']
        lo, hi = f30['lower_bound'], f30['upper_bound']
        hit = lo <= actual <= hi
        error_pct = round(abs(actual - f30['target']) / f30['target'] * 100, 2)

        p['actual_price'] = actual
        p['result']       = 'hit' if hit else 'miss'
        p['error_pct']    = error_pct
        p['status']       = 'completed'
        p['evaluated_date'] = today

        if not hit:
            direction = 'above' if actual > hi else 'below'
            p['notes'] = f"Actual price ${actual:,.2f} landed {direction} the confidence range (${lo:,.2f}–${hi:,.2f})."

        print(f"  {p['asset']}: actual=${actual} | {'HIT' if hit else 'MISS'} | error={error_pct}%")
        changed = True

    if changed:
        # Recompute summary
        completed = [p for p in data['predictions'] if p['status'] == 'completed']
        hits   = [p for p in completed if p['result'] == 'hit']
        misses = [p for p in completed if p['result'] == 'miss']
        pending = [p for p in data['predictions'] if p['status'] == 'pending']

        data['summary'] = {
            'total':            len(data['predictions']),
            'pending':          len(pending),
            'hits':             len(hits),
            'misses':           len(misses),
            'average_accuracy': round(
                sum(100 - p['error_pct'] for p in completed) / len(completed), 1
            ) if completed else None
        }

        with open(TRACK_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nTrack record updated: {len(hits)} hits, {len(misses)} misses, {len(pending)} pending.")
    else:
        print("\nNo predictions evaluated today.")

if __name__ == '__main__':
    evaluate()
