from datetime import date

import numpy as np
import pandas as pd
import pytest

from edgepulse import run as runner
from edgepulse.assets import ASSETS, LIVE_START
from tests.conftest import synthetic


class FakeStore:
    def __init__(self):
        self.prices = {}
        self.price_overwrite = {}
        self.forecasts = []

    def upsert_prices(self, asset, points, overwrite=True):
        self.prices.setdefault(asset, []).extend(points)
        self.price_overwrite[asset] = overwrite

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


def test_prices_are_only_overwritten_by_backfill():
    daily = FakeStore()
    runner.run("daily", store=daily, frame=frame(), today=date(2026, 10, 17))
    assert daily.price_overwrite and not any(daily.price_overwrite.values())
    backfill = FakeStore()
    runner.run("backfill", store=backfill, frame=frame(), today=date(2026, 10, 17))
    assert backfill.price_overwrite and all(backfill.price_overwrite.values())


def test_stale_prices_are_not_published_and_count_as_failures():
    store = FakeStore()
    failures = runner.run("daily", store=store, frame=frame(), today=date(2026, 11, 20))
    assert failures == len(ASSETS)
    assert store.forecasts == []
    assert store.prices == {}


def test_main_fails_when_any_market_fails(monkeypatch):
    monkeypatch.setattr(runner, "run", lambda mode: 1)
    with pytest.raises(SystemExit) as exc:
        runner.main(["daily"])
    assert exc.value.code == 1


def test_main_succeeds_when_no_market_fails(monkeypatch):
    monkeypatch.setattr(runner, "run", lambda mode: 0)
    runner.main(["daily"])
