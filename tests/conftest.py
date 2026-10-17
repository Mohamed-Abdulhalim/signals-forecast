import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def synthetic(start=date(2016, 1, 4), end=date(2026, 10, 16), seed=7, base=100.0):
    rnd = random.Random(seed)
    d, p, out = start, base, []
    while d <= end:
        if d.weekday() < 5:
            vol = 0.012 if d.year % 2 else 0.025
            p *= math.exp(rnd.gauss(0, vol))
            out.append((d, p))
        d += timedelta(days=1)
    return out


@pytest.fixture
def series():
    return synthetic()
