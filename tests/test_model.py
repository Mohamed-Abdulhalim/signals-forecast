import math
from datetime import date, timedelta

import numpy as np

from edgepulse.assets import COVERAGE, strength_label
from edgepulse.model import Model, clean_series, ewma_sigma, outcome_index


def test_clean_series_drops_one_day_spike_and_bad_values():
    d = date(2026, 1, 5)
    pts = [(d, 500), (d + timedelta(1), 169), (d + timedelta(2), 506), (d + timedelta(3), 0), (d + timedelta(4), None), (d + timedelta(5), 510)]
    out = clean_series(pts, 0.15)
    assert [c for _, c in out] == [500, 506, 510]


def test_clean_series_keeps_real_level_shift():
    d = date(2026, 3, 2)
    pts = [(d + timedelta(i), c) for i, c in enumerate([70, 71, 88, 89, 90])]
    assert len(clean_series(pts, 0.15)) == 5


def test_ewma_sigma_tracks_volatility():
    rng = np.random.default_rng(0)
    closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 500)))
    sig = ewma_sigma(closes)
    assert math.isnan(sig[5])
    assert 0.015 < np.nanmean(sig[100:]) < 0.025


def test_outcome_index_uses_first_close_on_or_after_target():
    dates = [date(2026, 1, 2) + timedelta(days=i) for i in range(0, 60, 3)]
    k = outcome_index(dates, 0)
    assert dates[k] >= dates[0] + timedelta(days=30)
    assert dates[k - 1] < dates[0] + timedelta(days=30)


def test_ranges_are_calibrated_on_random_walk(series):
    m = Model(series)
    held = []
    for f in m.backtest(series[0][0], date(2026, 9, 1)):
        i = m.dates.index(f["made_on"])
        k = outcome_index(m.dates, i)
        if k is not None:
            held.append(f["lo"] <= m.closes[k] <= f["hi"])
    assert len(held) > 300
    assert abs(np.mean(held) - COVERAGE) < 0.06


def test_calibration_never_uses_future_outcomes(series):
    m = Model(series)
    as_of = series[400][0]
    _, _, n, _ = m.quantiles(as_of)
    assert n == sum(1 for known_on, _ in m._z if known_on <= as_of)
    assert all(known_on <= as_of + timedelta(days=0) for known_on, _ in m._z[:n])


def test_forecast_shape_and_trend(series):
    m = Model(series)
    f = m.forecast(len(series) - 1)
    assert f["lo"] < f["price"] < f["hi"]
    assert f["trend"] in ("up", "down")
    assert (f["trend"] == "up") == (series[-1][1] > series[-64][1])
    assert f["target_on"] == series[-1][0] + timedelta(days=30)


def test_backtest_respects_end_and_spacing(series):
    m = Model(series)
    end = date(2025, 1, 1)
    bt = m.backtest(series[0][0], end, every=5)
    assert bt and all(f["made_on"] < end for f in bt)
    idx = [m.dates.index(f["made_on"]) for f in bt]
    assert min(b - a for a, b in zip(idx, idx[1:])) >= 5


def test_strength_label():
    assert strength_label(0.2) == "weak"
    assert strength_label(-1.0) == "moderate"
    assert strength_label(2.4) == "strong"
