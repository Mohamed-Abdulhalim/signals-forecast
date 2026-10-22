import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests
from flask import Flask, Response, jsonify, redirect, render_template

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from edgepulse.assets import ASSETS, BY_NAME, COVERAGE, HORIZON_DAYS, LIVE_START, TREND_LOOKBACK, strength_label

app = Flask(__name__)

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "https://zajbilbmvapbfakorfez.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "sb_publishable_DY1lG2FW7E37L9myVOiuUg_BBw1qn1x"
SITE_URL = "https://edgepulse.halim.pro"
CACHE_TTL = 600
CHART_DAYS = 370

_cache = {}


def _rpc(name):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if not SUPABASE_KEY.startswith("sb_"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/{name}", headers=headers, json={}, timeout=15)
    r.raise_for_status()
    return r.json()


def cached(name):
    now = time.time()
    hit = _cache.get(name)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        value = _rpc(name)
    except Exception:
        return hit[1] if hit else None
    if value:
        _cache[name] = (now, value)
    return value


def fmt(value, decimals):
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def pct(value):
    if value is None:
        return None
    return round(value * 100, 1)


def build_assets(raw):
    rows = {r["asset"]: r for r in (raw or [])}
    out = []
    for cfg in ASSETS:
        r = rows.get(cfg["name"])
        if not r or r.get("last") is None:
            continue
        d = cfg["decimals"]
        last, prev = r.get("last"), r.get("prev")
        f = r.get("forecast") or {}
        stats = r.get("stats") or {}
        bt = stats.get("backtest") or {}
        lv = stats.get("live") or {}
        history = r.get("history") or []
        item = {
            "name": cfg["name"],
            "slug": cfg["name"].lower().replace(" ", "-"),
            "category": cfg["category"],
            "unit": cfg["unit"],
            "ticker": cfg["ticker"],
            "price": fmt(last, d),
            "last_day": r.get("last_day"),
            "change_pct": round((last / prev - 1) * 100, 2) if prev else None,
            "history": history[-CHART_DAYS:],
            "decimals": d,
            "forecast": None,
            "backtest": {"n": bt.get("n", 0), "trend": pct(bt.get("trend_rate")), "range": pct(bt.get("range_rate")), "up": pct(bt.get("up_rate"))},
            "live": {"n": lv.get("n", 0), "trend": pct(lv.get("trend_rate")), "range": pct(lv.get("range_rate"))},
        }
        if f:
            item["forecast"] = {
                "made_on": f.get("made_on"),
                "target_on": f.get("target_on"),
                "kind": f.get("kind"),
                "price": f.get("price"),
                "trend": f.get("trend"),
                "strength": strength_label(f.get("trend_strength") or 0),
                "lo": fmt(f.get("lo"), d),
                "hi": fmt(f.get("hi"), d),
                "lo_raw": f.get("lo"),
                "hi_raw": f.get("hi"),
                "lo_pct": round((f["lo"] / f["price"] - 1) * 100, 1),
                "hi_pct": round((f["hi"] / f["price"] - 1) * 100, 1),
                "vol": round((f.get("vol_annual") or 0) * 100),
                "coverage": round((f.get("coverage") or COVERAGE) * 100),
            }
        out.append(item)
    return out


def build_track(raw):
    raw = raw or {}
    totals = {t["kind"]: t for t in raw.get("totals") or []}

    def due(day):
        try:
            return (date.fromisoformat(day) + timedelta(days=HORIZON_DAYS)).isoformat()
        except (TypeError, ValueError):
            return None

    def total(kind):
        t = totals.get(kind) or {}
        return {
            "completed": t.get("completed") or 0,
            "pending": t.get("pending") or 0,
            "trend": pct(t.get("trend_rate")),
            "range": pct(t.get("range_rate")),
            "up": pct(t.get("up_rate")),
            "first_on": t.get("first_on"),
            "first_due": due(t.get("first_on")),
            "last_on": t.get("last_on"),
        }

    per_asset = []
    for s in raw.get("summary") or []:
        if s.get("asset") not in BY_NAME:
            continue
        per_asset.append({
            "kind": s["kind"],
            "asset": s["asset"],
            "completed": s.get("completed") or 0,
            "pending": s.get("pending") or 0,
            "trend": pct(s.get("trend_rate")),
            "range": pct(s.get("range_rate")),
            "up": pct(s.get("up_rate")),
            "best_constant": pct(max(s["up_rate"], 1 - s["up_rate"])) if s.get("up_rate") is not None else None,
        })
    order = {a["name"]: i for i, a in enumerate(ASSETS)}
    per_asset.sort(key=lambda x: (x["kind"] != "live", order.get(x["asset"], 99)))

    recent = []
    for r in raw.get("recent") or []:
        cfg = BY_NAME.get(r["asset"])
        if not cfg:
            continue
        d = cfg["decimals"]
        recent.append({
            "asset": r["asset"],
            "kind": r["kind"],
            "made_on": r["made_on"],
            "target_on": r["target_on"],
            "price": fmt(r["price"], d),
            "trend": r["trend"],
            "range": f"{fmt(r['lo'], d)} – {fmt(r['hi'], d)}",
            "actual": fmt(r["actual"], d) if r.get("actual") is not None else None,
            "trend_hit": r.get("trend_hit"),
            "in_range": r.get("in_range"),
        })
    return {"live": total("live"), "backtest": total("backtest"), "per_asset": per_asset, "recent": recent}


@app.context_processor
def inject_globals():
    return {
        "coverage_pct": round(COVERAGE * 100),
        "horizon_days": HORIZON_DAYS,
        "trend_days": TREND_LOOKBACK,
        "live_start": LIVE_START.isoformat(),
        "year": date.today().year,
    }


@app.route("/")
def home():
    raw = cached("dashboard")
    assets = build_assets(raw)
    track = build_track(cached("track_record"))
    last_day = max((a["last_day"] for a in assets if a["last_day"]), default=None)
    return render_template("index.html", assets=assets, track=track, last_day=last_day, unavailable=raw is None)


@app.route("/track-record")
def track_record():
    raw = cached("track_record")
    return render_template("track_record.html", track=build_track(raw), unavailable=raw is None)


@app.route("/methodology")
def methodology():
    return render_template("methodology.html", assets=ASSETS)


@app.route("/work-with-me")
def work_with_me():
    return render_template("work_with_me.html")


@app.route("/signals")
@app.route("/forecasts")
def old_pages():
    return redirect("/", code=301)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(build_assets(cached("dashboard")))


@app.route("/api/track-record")
def api_track_record():
    return jsonify(build_track(cached("track_record")))


@app.route("/health")
def health():
    return "ok", 200


@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    today = datetime.now(timezone.utc).date().isoformat()
    urls = ["/", "/track-record", "/methodology", "/work-with-me"]
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    body += [f"<url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls]
    body.append("</urlset>")
    return Response("\n".join(body), mimetype="application/xml")


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
