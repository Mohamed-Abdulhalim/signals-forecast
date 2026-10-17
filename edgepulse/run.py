import argparse
import sys
from datetime import date, timedelta

from edgepulse.assets import ASSETS, LIVE_START, MODEL_VERSION
from edgepulse.collect import fetch_history, series_for
from edgepulse.model import Model
from edgepulse.store import Store


def run(mode, store=None, frame=None, today=None):
    today = today or date.today()
    store = store or Store()
    frame = frame if frame is not None else fetch_history([a["ticker"] for a in ASSETS])
    report = []
    failures = 0
    for asset in ASSETS:
        name = asset["name"]
        points = series_for(frame, asset)
        if len(points) < 300:
            print(f"[skip] {name}: only {len(points)} usable prices")
            failures += 1
            continue
        if points[-1][0] < today - timedelta(days=7):
            print(f"[warn] {name}: latest price is from {points[-1][0]}")
        recent = points if mode == "backfill" else [p for p in points if p[0] >= today - timedelta(days=45)]
        store.upsert_prices(name, recent)
        model = Model(points)
        if mode == "backfill":
            backtests = model.backtest(start=points[0][0], end=LIVE_START)
            store.upsert_forecasts(name, "backtest", backtests, MODEL_VERSION)
            report.append(f"{name}: {len(points)} prices {points[0][0]}..{points[-1][0]}, {len(backtests)} backtests")
        live = model.forecast(len(points) - 1)
        if live and live["made_on"] >= LIVE_START:
            store.upsert_forecasts(name, "live", [live], MODEL_VERSION)
            report.append(
                f"{name}: live {live['made_on']} price {live['price']:.4g} trend {live['trend']} "
                f"range {live['lo']:.4g}-{live['hi']:.4g} (n={live['calibration_samples']})"
            )
    print("\n".join(report))
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["daily", "backfill"])
    args = ap.parse_args(argv)
    failures = run(args.mode)
    if failures == len(ASSETS):
        sys.exit(1)


if __name__ == "__main__":
    main()
