import math
from bisect import bisect_left
from datetime import timedelta

import numpy as np

from edgepulse.assets import COVERAGE, HORIZON_DAYS, TREND_LOOKBACK

EWMA_LAMBDA = 0.94
TRADING_DAYS_PER_HORIZON = 21
MIN_CALIBRATION_SAMPLES = 150
NORMAL_Z = {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.9600}


def clean_series(points, spike):
    pts = sorted((d, float(c)) for d, c in points if c is not None and float(c) > 0 and math.isfinite(float(c)))
    dedup = []
    for d, c in pts:
        if dedup and dedup[-1][0] == d:
            dedup[-1] = (d, c)
        else:
            dedup.append((d, c))
    out = []
    for i, (d, c) in enumerate(dedup):
        if 0 < i < len(dedup) - 1:
            prev_c = dedup[i - 1][1]
            next_c = dedup[i + 1][1]
            up = math.log(c / prev_c)
            back = math.log(next_c / c)
            if abs(up) > spike and abs(back) > spike and up * back < 0:
                continue
        out.append((d, c))
    return out


def ewma_sigma(closes):
    closes = np.asarray(closes, dtype=float)
    rets = np.diff(np.log(closes))
    sigma = np.full(len(closes), np.nan)
    if len(rets) < 20:
        return sigma
    var = float(np.var(rets[:20]))
    for t in range(1, len(closes)):
        var = EWMA_LAMBDA * var + (1 - EWMA_LAMBDA) * rets[t - 1] ** 2
        if t >= 20:
            sigma[t] = math.sqrt(var)
    return sigma


def outcome_index(dates, i, horizon_days=HORIZON_DAYS):
    target = dates[i] + timedelta(days=horizon_days)
    k = bisect_left(dates, target)
    if k < len(dates) and dates[k] <= target + timedelta(days=7):
        return k
    return None


class Model:
    def __init__(self, points, coverage=COVERAGE):
        self.dates = [d for d, _ in points]
        self.closes = np.array([c for _, c in points], dtype=float)
        self.sigma = ewma_sigma(self.closes)
        self.coverage = coverage
        self._z = []
        for j in range(len(self.dates)):
            k = outcome_index(self.dates, j)
            if k is None or not math.isfinite(self.sigma[j]) or self.sigma[j] <= 0:
                continue
            z = math.log(self.closes[k] / self.closes[j]) / (self.sigma[j] * math.sqrt(TRADING_DAYS_PER_HORIZON))
            self._z.append((self.dates[k], z))

    def quantiles(self, as_of):
        known = [z for known_on, z in self._z if known_on <= as_of]
        if len(known) < MIN_CALIBRATION_SAMPLES:
            z = NORMAL_Z.get(self.coverage, 1.6449)
            return -z, z, len(known), False
        tail = (1 - self.coverage) / 2
        lo, hi = np.quantile(known, [tail, 1 - tail])
        return float(lo), float(hi), len(known), True

    def can_forecast(self, i):
        return i >= TREND_LOOKBACK and math.isfinite(self.sigma[i]) and self.sigma[i] > 0

    def forecast(self, i):
        if not self.can_forecast(i):
            return None
        price = float(self.closes[i])
        sig = float(self.sigma[i])
        trend_ret = math.log(price / self.closes[i - TREND_LOOKBACK])
        strength = trend_ret / (sig * math.sqrt(TREND_LOOKBACK))
        q_lo, q_hi, n, empirical = self.quantiles(self.dates[i])
        scale = sig * math.sqrt(TRADING_DAYS_PER_HORIZON)
        return {
            "made_on": self.dates[i],
            "price": price,
            "trend": "up" if trend_ret > 0 else "down",
            "trend_strength": round(strength, 4),
            "vol_annual": round(sig * math.sqrt(252), 6),
            "lo": price * math.exp(q_lo * scale),
            "hi": price * math.exp(q_hi * scale),
            "coverage": self.coverage,
            "target_on": self.dates[i] + timedelta(days=HORIZON_DAYS),
            "calibration_samples": n,
            "calibrated": empirical,
        }

    def backtest(self, start, end, every=5, warmup_samples=MIN_CALIBRATION_SAMPLES):
        out = []
        last = None
        for i, d in enumerate(self.dates):
            if d < start or d >= end:
                continue
            if last is not None and i - last < every:
                continue
            f = self.forecast(i)
            if f is None or f["calibration_samples"] < warmup_samples:
                continue
            out.append(f)
            last = i
        return out

