"""
fix_gold_prices.py

One-time script to correct Gold prices in all existing data files.
No API calls needed.

GLD ETF currently trades at ~$276 per share.
Real gold spot price is ~$2,980 per troy oz.
Scale factor: 2980 / 276 = 10.797

We multiply all stored Gold prices by this factor to get real spot prices.

Run once from GitHub Actions.
"""

import json
import os
from datetime import datetime

DATA_DIR = 'data/prices'

# Real gold spot price as of March 2026 / GLD ETF price
# GLD tracks gold at ~1/10th of spot price
REAL_GOLD_SPOT = 2980.0   # approximate current spot price USD
GLD_CURRENT    = 276.0    # approximate current GLD ETF price
SCALE_FACTOR   = REAL_GOLD_SPOT / GLD_CURRENT

print(f"Scale factor: {SCALE_FACTOR:.4f}")
print(f"Example: GLD $476.24 → Gold ${476.24 * SCALE_FACTOR:,.2f}")
print(f"Scanning {DATA_DIR}...\n")

updated_files  = 0
updated_prices = 0

for filename in sorted(os.listdir(DATA_DIR)):
    if not filename.startswith('safe_haven_') or not filename.endswith('.json'):
        continue

    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath) as f:
        data = json.load(f)

    changed = False
    for asset in data.get('assets', []):
        if asset['asset'] == 'Gold':
            old_price = asset['price']
            # Only scale if price looks like GLD range (100-600)
            # Real gold is 1500-3500, so this prevents double-scaling
            if old_price < 1000:
                asset['price'] = round(old_price * SCALE_FACTOR, 2)
                print(f"  {filename}: Gold ${old_price} → ${asset['price']}")
                changed        = True
                updated_prices += 1

    if changed:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        updated_files += 1

print(f"\nDone. Updated {updated_prices} Gold prices across {updated_files} files.")
print("Next:  python analysis/signals.py")
print("       python analysis/forecasts.py")
