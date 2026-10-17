import pytest

from web import app as web


DASH = [
    {"asset": "Gold", "last": 4187.46, "prev": 4150.0, "last_day": "2026-10-16",
     "history": [["2026-10-15", 4150.0], ["2026-10-16", 4187.46]],
     "forecast": {"made_on": "2026-10-16", "kind": "live", "price": 4187.46, "trend": "up", "trend_strength": 1.8,
                  "vol_annual": 0.18, "lo": 3900.0, "hi": 4500.0, "coverage": 0.9, "target_on": "2026-11-15"},
     "stats": {"backtest": {"n": 400, "trend_rate": 0.56, "range_rate": 0.88, "up_rate": 0.54}}},
    {"asset": "Wheat", "last": 5.2125, "prev": None, "last_day": "2026-10-16", "history": [], "forecast": None, "stats": None},
]
TRACK = {
    "totals": [{"kind": "backtest", "completed": 3000, "pending": 20, "trend_rate": 0.53, "range_rate": 0.87, "up_rate": 0.51, "first_on": "2017-01-02", "last_on": "2026-10-09"},
               {"kind": "live", "completed": 0, "pending": 7, "trend_rate": None, "range_rate": None, "up_rate": None, "first_on": "2026-10-16", "last_on": "2026-10-16"}],
    "summary": [{"kind": "backtest", "asset": "Gold", "completed": 400, "pending": 3, "trend_rate": 0.56, "range_rate": 0.88, "up_rate": 0.54}],
    "recent": [{"asset": "Gold", "made_on": "2026-10-16", "kind": "live", "price": 4187.46, "trend": "up", "lo": 3900.0, "hi": 4500.0,
                "target_on": "2026-11-15", "actual_on": None, "actual": None, "trend_hit": None, "in_range": None},
               {"asset": "Gold", "made_on": "2026-08-01", "kind": "backtest", "price": 4000.0, "trend": "down", "lo": 3700.0, "hi": 4300.0,
                "target_on": "2026-08-31", "actual_on": "2026-08-31", "actual": 4100.0, "trend_hit": False, "in_range": True}],
}


@pytest.fixture
def client(monkeypatch):
    web._cache.clear()
    monkeypatch.setattr(web, "_rpc", lambda name: {"dashboard": DASH, "track_record": TRACK}[name])
    web.app.config["TESTING"] = True
    return web.app.test_client()


def test_home_renders_correct_units_and_range(client):
    html = client.get("/").get_data(as_text=True)
    assert "4,187.46" in html and "$ / troy oz" in html
    assert "3,900.00 – 4,500.00" in html
    assert "5.213" in html and "$ / bushel" in html
    assert "95%" not in html
    assert "88.0%" in html or "87.0%" in html


def test_track_record_page(client):
    html = client.get("/track-record").get_data(as_text=True)
    assert "Ranges that held" in html
    assert "held" in html and "wrong" in html and "open" in html


def test_pages_and_redirects(client):
    assert client.get("/methodology").status_code == 200
    assert client.get("/work-with-me").status_code == 200
    assert client.get("/signals").status_code == 301
    assert client.get("/nope").status_code == 404
    assert b"sitemap.xml" in client.get("/robots.txt").data


def test_api_and_outage(client, monkeypatch):
    assert client.get("/api/dashboard").get_json()[0]["name"] == "Gold"
    web._cache.clear()

    def down(name):
        raise RuntimeError("down")

    monkeypatch.setattr(web, "_rpc", down)
    r = client.get("/")
    assert r.status_code == 200
    assert "temporarily unavailable" in r.get_data(as_text=True)


def test_empty_response_is_not_cached(monkeypatch):
    web._cache.clear()
    calls = []

    def rpc(name):
        calls.append(name)
        return [] if len(calls) == 1 else DASH

    monkeypatch.setattr(web, "_rpc", rpc)
    assert web.cached("dashboard") == []
    assert web.cached("dashboard") == DASH
