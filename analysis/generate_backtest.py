"""
generate_backtest.py

Runs daily via GitHub Actions.
Reads historical price files in data/prices/, generates completed
backtest entries for every 30-day window where we have both entry
and exit prices. Adds new entries to track_record.json without
touching any existing pending or completed entries.

Labeled clearly as 'backtest' — honest, transparent, and credible.
"""

import json
import os
from datetime import datetime, timedelta

DATA_DIR   = 'data/prices'
TRACK_FILE = 'data/track_record.json'

# How many days define a "completed cycle"
WINDOW_DAYS = 30

# Minimum price move to generate a signal (avoids flat/noisy periods)
MIN_MOVE_PCT = 0.5

# Assets and which category file they live in
ASSET_CATEGORIES = {
    'Brent Oil':   'energy',
    'Natural Gas': 'energy',
    'Gold':        'safe_haven',
    'USD Index':   'safe_haven',
    'Wheat':       'food',
    'Corn':        'food',
    'Rice':        'food',
}


# ── File helpers ─────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


# ── Price file reader ─────────────────────────────────────────

def load_all_prices():
    """
    Read all daily price files and return:
    { asset_name: { 'YYYY-MM-DD': price, ... }, ... }
    """
    prices = {asset: {} for asset in ASSET_CATEGORIES}

    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] {DATA_DIR} not found.")
        return prices

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(DATA_DIR, fname)
        data  = load_json(fpath)
        if not data or 'assets' not in data:
            continue
        for asset_entry in data['assets']:
            asset = asset_entry.get('asset')
            price = asset_entry.get('price')
            date  = asset_entry.get('date')
            if asset in prices and price and date:
                prices[asset][date] = float(price)

    for asset, history in prices.items():
        print(f"  {asset}: {len(history)} price points loaded")

    return prices


# ── Signal logic ──────────────────────────────────────────────

def derive_signal(prices_30d):
    """
    Given a list of ~30 daily prices (oldest first),
    derive the signal that would have been generated.
    Returns: (signal, confidence, momentum_score)
    """
    if len(prices_30d) < 10:
        return None, None, None

    closes    = prices_30d
    recent    = closes[-5:]
    older     = closes[-15:-5]
    very_old  = closes[:10]

    recent_avg   = sum(recent) / len(recent)
    older_avg    = sum(older) / len(older)
    very_old_avg = sum(very_old) / len(very_old)

    # Momentum: how much recent avg moved vs older avg
    if older_avg == 0:
        return None, None, None

    momentum = (recent_avg - older_avg) / older_avg

    # Trend over full window
    full_trend = (recent_avg - very_old_avg) / very_old_avg if very_old_avg else 0

    # Signal direction
    if momentum > 0.005:
        signal = 'bullish'
    elif momentum < -0.005:
        signal = 'bearish'
    else:
        signal = 'neutral'

    # Confidence based on agreement between momentum and full trend
    same_direction = (momentum > 0 and full_trend > 0) or (momentum < 0 and full_trend < 0)
    abs_mom = abs(momentum)

    if abs_mom > 0.03 and same_direction:
        confidence = 'high'
    elif abs_mom > 0.01:
        confidence = 'medium'
    else:
        confidence = 'low'

    momentum_score = round(min(abs(momentum) * 20, 1.0), 2)

    return signal, confidence, momentum_score


def derive_forecast(entry_price, prices_30d, signal):
    """
    Derive what the forecast target + bounds would have been.
    Simple linear projection based on recent trend.
    """
    if len(prices_30d) < 10 or entry_price == 0:
        return None

    recent_avg = sum(prices_30d[-5:]) / 5
    older_avg  = sum(prices_30d[-15:-5]) / 10 if len(prices_30d) >= 15 else entry_price

    trend_pct = (recent_avg - older_avg) / older_avg if older_avg else 0

    # Clamp trend to ±30% to prevent runaway projections on sharp moves
    trend_pct = max(-0.30, min(0.30, trend_pct))

    # Project 30 days forward
    target = round(entry_price * (1 + trend_pct * 2), 2)

    # Floor: target can never go below 10% of entry price
    # (negative commodity prices are not meaningful for this use case)
    floor  = round(entry_price * 0.10, 2)
    target = max(target, floor)

    # Confidence band: ~5% of entry price
    band  = entry_price * 0.05
    lower = round(max(target - band, floor), 2)
    upper = round(target + band, 2)

    # Ensure correct order
    if lower > upper:
        lower, upper = upper, lower

    return {
        'target':      target,
        'lower_bound': lower,
        'upper_bound': upper,
    }


# ── Hit/miss evaluation ───────────────────────────────────────

def evaluate_outcome(signal, entry_price, exit_price, forecast):
    """
    Two independent accuracy measures:

    1. Band accuracy (result): did actual price land within the forecast band?
       This is strict — a 5% band is a demanding target.

    2. Directional accuracy (direction_correct): did price move the way
       the signal predicted?
       - bullish → exit_price > entry_price  = correct
       - bearish → exit_price < entry_price  = correct
       - neutral → abs move < 2%             = correct (price stayed flat)

    Both are tracked separately in the entry and in the summary.
    Directional accuracy is the more meaningful metric for
    hedging/positioning decisions.
    """
    if not forecast or exit_price is None:
        return None, None, None, None

    # Band accuracy
    lo, hi  = forecast['lower_bound'], forecast['upper_bound']
    hit      = lo <= exit_price <= hi
    error    = round(abs(exit_price - forecast['target']) / forecast['target'] * 100, 2)

    # Directional accuracy
    move_pct = (exit_price - entry_price) / entry_price * 100
    if signal == 'bullish':
        direction_correct = exit_price > entry_price
    elif signal == 'bearish':
        direction_correct = exit_price < entry_price
    else:  # neutral — price stayed within ±2%
        direction_correct = abs(move_pct) <= 2.0

    notes = None
    if not hit:
        direction = 'above' if exit_price > hi else 'below'
        dir_str   = '✓ direction correct' if direction_correct else '✗ direction wrong'
        notes = (f"Actual ${exit_price:,.2f} landed {direction} "
                 f"the band (${lo:,.2f}–${hi:,.2f}). {dir_str}.")

    return ('hit' if hit else 'miss'), error, direction_correct, notes


# ── Main ─────────────────────────────────────────────────────

def main():
    print("=" * 57)
    print("  EdgePulse — Rolling Backtest Generator")
    print("=" * 57)

    # Load price history
    print("\n[1/4] Loading price files...")
    all_prices = load_all_prices()

    # Load or create track record
    print("\n[2/4] Loading track record...")
    if os.path.exists(TRACK_FILE):
        track = load_json(TRACK_FILE)
    else:
        track = {'predictions': [], 'summary': {}}

    if 'predictions' not in track:
        track['predictions'] = []

    # Build set of existing IDs to avoid duplicates
    existing_ids = {p['id'] for p in track['predictions']}
    print(f"  Existing entries: {len(existing_ids)}")

    # Generate backtest entries
    print("\n[3/4] Generating backtest cycles...")
    new_entries = []
    today_str   = datetime.now().strftime('%Y-%m-%d')

    for asset, history in all_prices.items():
        if not history:
            continue

        sorted_dates = sorted(history.keys())

        for i, entry_date in enumerate(sorted_dates):
            # Find exit date ~30 days later
            entry_dt  = datetime.strptime(entry_date, '%Y-%m-%d')
            exit_dt   = entry_dt + timedelta(days=WINDOW_DAYS)
            exit_date = exit_dt.strftime('%Y-%m-%d')

            # Skip if exit is today or in the future
            if exit_date >= today_str:
                continue

            # Find closest available exit price
            exit_price = None
            for offset in range(0, 5):
                candidate = (exit_dt + timedelta(days=offset)).strftime('%Y-%m-%d')
                if candidate in history:
                    exit_price = history[candidate]
                    break
            if exit_price is None:
                continue

            entry_price = history[entry_date]

            # Skip tiny moves — not meaningful
            move_pct = abs(exit_price - entry_price) / entry_price * 100
            if move_pct < MIN_MOVE_PCT:
                continue

            # Build signal from prices in the 30 days BEFORE entry
            lookback_dates = [
                (entry_dt - timedelta(days=j)).strftime('%Y-%m-%d')
                for j in range(30, 0, -1)
            ]
            lookback_prices = [history[d] for d in lookback_dates if d in history]

            if len(lookback_prices) < 10:
                # Not enough history before this date — skip
                continue

            signal, confidence, momentum = derive_signal(lookback_prices)
            if not signal:
                continue

            forecast = derive_forecast(entry_price, lookback_prices, signal)
            if not forecast:
                continue

            result, error_pct, direction_correct, notes = evaluate_outcome(
                signal, entry_price, exit_price, forecast)
            if result is None:
                continue

            # Build unique ID
            asset_slug = asset.lower().replace(' ', '-')
            date_slug  = entry_date.replace('-', '')
            entry_id   = f"backtest-{asset_slug}-{date_slug}"

            if entry_id in existing_ids:
                continue  # Already recorded

            entry = {
                'id':                 entry_id,
                'type':               'backtest',
                'asset':              asset,
                'signal':             signal,
                'signal_confidence':  confidence,
                'momentum_score':     momentum,
                'prediction_date':    entry_date,
                'current_price':      entry_price,
                'forecast_30_days':   forecast,
                'outcome_date':       exit_date,
                'actual_price':       exit_price,
                'status':             'completed',
                'result':             result,
                'direction_correct':  direction_correct,
                'error_pct':          error_pct,
                'evaluated_date':     today_str,
                'notes':              notes,
            }

            new_entries.append(entry)
            existing_ids.add(entry_id)

    print(f"  New backtest entries: {len(new_entries)}")

    if not new_entries:
        print("\nNothing new to add today.")
        return

    # Append new entries (backtests go before live predictions)
    live_predictions = [p for p in track['predictions'] if p.get('type') != 'backtest']
    old_backtests    = [p for p in track['predictions'] if p.get('type') == 'backtest']

    # Sort new + old backtests by date
    all_backtests = old_backtests + new_entries
    all_backtests.sort(key=lambda p: p['prediction_date'])

    track['predictions'] = all_backtests + live_predictions

    # Recompute summary
    print("\n[4/4] Updating summary...")
    completed  = [p for p in track['predictions'] if p['status'] == 'completed']
    hits       = [p for p in completed if p['result'] == 'hit']
    misses     = [p for p in completed if p['result'] == 'miss']
    pending    = [p for p in track['predictions'] if p['status'] == 'pending']

    # Directional accuracy — only count entries that have the field
    dir_entries = [p for p in completed if 'direction_correct' in p]
    dir_correct = [p for p in dir_entries if p['direction_correct']]

    track['summary'] = {
        'total':                len(track['predictions']),
        'pending':              len(pending),
        'completed':            len(completed),
        'hits':                 len(hits),
        'misses':               len(misses),
        'hit_rate':             round(len(hits) / len(completed) * 100, 1) if completed else None,
        'directional_correct':  len(dir_correct),
        'directional_total':    len(dir_entries),
        'directional_accuracy': round(len(dir_correct) / len(dir_entries) * 100, 1) if dir_entries else None,
        'average_accuracy':     round(
            sum(100 - p['error_pct'] for p in completed) / len(completed), 1
        ) if completed else None,
        'last_updated':         today_str,
    }

    save_json(TRACK_FILE, track)

    print(f"\n  Saved {len(track['predictions'])} total entries.")
    print(f"  Backtests: {len(all_backtests)} | Live: {len(live_predictions)}")
    print(f"  Band hit rate:       {track['summary']['hit_rate']}% over {len(completed)} cycles")
    print(f"  Directional accuracy:{track['summary']['directional_accuracy']}% over {len(dir_entries)} cycles")
    print("\n  Done.")


if __name__ == '__main__':
    main()
