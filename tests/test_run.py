from datetime import date

import numpy as np
import pandas as pd

from edgepulse import run as runner
from edgepulse.assets import ASSETS, LIVE_START
from tests.conftest import synthetic


class FakeStore:
    def __init__(self):
        self.prices = {}
        self.forecasts = []

    def upsert_prices(self, asset, points):
        self.prices.setdefault(asset, []).extend(points)

    def upsert_forecasts(self, asset, kind, forecasts, model):
        self.forecasts += [(asset, kind, f) for f in forecasts]


def frame():
    pts = synthetic()
    idx = pd.to_datetime([d for d, _ in pts])
    data = {}
    for i, a in enumerate(ASSETS[:3]):
        closes = np.array([c for _, c in pts]) * (i + 1) * a["divisor"]
        data[(a["ticker"], "Close")] = closes
        data[(a["ticker"], "Open")] = closes
    return pd.DataFrame(data, index=idx)


def test_backfill_writes_backtests_before_live_start_and_one_live():
    store = FakeStore()
    failures = runner.run("backfill", store=store, frame=frame(), today=date(2026, 10, 17))
    assert failures == len(ASSETS) - 3
    kinds = {}
    for asset, kind, f in store.forecasts:
        kinds.setdefault(kind, []).append(f)
        if kind == "backtest":
            assert f["made_on"] < LIVE_START
    assert len(kinds["live"]) == 3
    assert all(f["made_on"] >= LIVE_START for f in kinds["live"])
    assert len(kinds["backtest"]) > 600


def test_daily_only_pushes_recent_prices():
    store = FakeStore()
    runner.run("daily", store=store, frame=frame(), today=date(2026, 10, 17))
    for points in store.prices.values():
        assert len(points) < 40
    assert all(kind == "live" for _, kind, _ in store.forecasts)
