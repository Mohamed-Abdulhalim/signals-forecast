from datetime import date

from edgepulse.store import Store


class Response:
    status_code = 201
    text = ""


class Session:
    def __init__(self):
        self.calls = []

    def post(self, url, params=None, headers=None, data=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "data": data})
        return Response()


def forecast(day):
    return {
        "made_on": day, "price": 100.0, "trend": "up", "trend_strength": 1.0, "vol_annual": 0.2,
        "lo": 90.0, "hi": 110.0, "coverage": 0.9, "target_on": date(2026, 11, 20),
    }


def store():
    session = Session()
    return Store(key="sb_secret_test", session=session), session


def test_live_forecasts_are_never_overwritten():
    s, session = store()
    s.upsert_forecasts("Gold", "live", [forecast(date(2026, 10, 21))], "v2")
    assert "ignore-duplicates" in session.calls[0]["headers"]["Prefer"]
    assert "merge-duplicates" not in session.calls[0]["headers"]["Prefer"]


def test_backtests_can_be_rebuilt():
    s, session = store()
    s.upsert_forecasts("Gold", "backtest", [forecast(date(2026, 1, 5))], "v2")
    assert "merge-duplicates" in session.calls[0]["headers"]["Prefer"]


def test_prices_overwrite_only_when_asked():
    s, session = store()
    points = [(date(2026, 10, 21), 4131.9)]
    s.upsert_prices("Gold", points)
    s.upsert_prices("Gold", points, overwrite=False)
    assert "merge-duplicates" in session.calls[0]["headers"]["Prefer"]
    assert "ignore-duplicates" in session.calls[1]["headers"]["Prefer"]
