from datetime import date

LIVE_START = date(2026, 10, 16)
MODEL_VERSION = "v2"
HORIZON_DAYS = 30
TREND_LOOKBACK = 63
COVERAGE = 0.90

ASSETS = [
    {"name": "Brent Oil", "ticker": "BZ=F", "category": "Energy", "unit": "$ / barrel", "divisor": 1, "decimals": 2, "spike": 0.15},
    {"name": "Natural Gas", "ticker": "NG=F", "category": "Energy", "unit": "$ / MMBtu", "divisor": 1, "decimals": 3, "spike": 0.25},
    {"name": "Gold", "ticker": "GC=F", "category": "Safe haven", "unit": "$ / troy oz", "divisor": 1, "decimals": 2, "spike": 0.10},
    {"name": "USD Index", "ticker": "DX-Y.NYB", "category": "Safe haven", "unit": "index points", "divisor": 1, "decimals": 2, "spike": 0.05},
    {"name": "Wheat", "ticker": "ZW=F", "category": "Food", "unit": "$ / bushel", "divisor": 100, "decimals": 3, "spike": 0.15},
    {"name": "Corn", "ticker": "ZC=F", "category": "Food", "unit": "$ / bushel", "divisor": 100, "decimals": 3, "spike": 0.15},
    {"name": "Rough Rice", "ticker": "ZR=F", "category": "Food", "unit": "$ / cwt", "divisor": 1, "decimals": 2, "spike": 0.15},
]

BY_NAME = {a["name"]: a for a in ASSETS}


def strength_label(strength):
    s = abs(strength)
    if s < 0.5:
        return "weak"
    if s < 1.5:
        return "moderate"
    return "strong"
