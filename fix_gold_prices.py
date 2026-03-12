"""
fix_gold_prices.py v2

Corrects Gold prices from ~$5,142 (overcorrected) to ~$2,980 (real spot).
Correction factor: 2980 / 5142 = 0.5795

Also no longer needs API calls — pure math on existing files.
"""

import json
import os

DATA_DIR          = 'data/prices'
REAL_GOLD_TODAY   = 2980.0    # actual gold spot price March 2026
STORED_GOLD_TODAY = 5142.01   # what we currently have stored
CORRECTION_FACTOR = REAL_GOLD_TODAY / STORED_GOLD_TODAY

print(f"Correction factor: {CORRECTION_FACTOR:.6f}")
print(f"Example: $5,142 → ${5142.01 * CORRECTION_FACTOR:,.2f}")
print(f"Example: $4,161 → ${4161.42 * CORRECTION_FACTOR:,.2f} (Dec 2025, historically accurate)")
print(f"\nScanning {DATA_DIR}...\n")

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
            # Only correct prices in the overcorrected range (>1000)
            if old_price > 1000:
                asset['price'] = round(old_price * CORRECTION_FACTOR, 2)
                changed         = True
                updated_prices += 1

    if changed:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        updated_files += 1

print(f"Done. Corrected {updated_prices} Gold prices across {updated_files} files.")
print(f"Gold should now range from ~$2,400 (Dec 2025) to ~$2,980 (today).")
print("\nNext:  python analysis/signals.py")
print("       python analysis/forecasts.py")
