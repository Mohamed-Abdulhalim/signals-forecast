"""
reset_backtests.py

Run ONCE to strip all backtest entries from track_record.json,
preserving live predictions. The daily workflow will immediately
regenerate backtests with the new direction_correct field.
"""

import json
import os

TRACK_FILE = 'data/track_record.json'

def main():
    if not os.path.exists(TRACK_FILE):
        print("No track_record.json found.")
        return

    with open(TRACK_FILE) as f:
        track = json.load(f)

    all_preds   = track.get('predictions', [])
    live        = [p for p in all_preds if p.get('type') != 'backtest']
    backtests   = [p for p in all_preds if p.get('type') == 'backtest']

    print(f"Found {len(all_preds)} total entries:")
    print(f"  Live predictions: {len(live)}")
    print(f"  Backtest entries: {len(backtests)} → removing")

    track['predictions'] = live
    track['summary']     = {}

    with open(TRACK_FILE, 'w') as f:
        json.dump(track, f, indent=2)

    print(f"\nDone. {len(live)} live predictions kept.")
    print("Now run the 'Evaluate Predictions' workflow to regenerate backtests.")

if __name__ == '__main__':
    main()
