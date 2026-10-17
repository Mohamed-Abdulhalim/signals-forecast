import json
import os
from datetime import date

import requests

PUBLIC_URL = "https://zajbilbmvapbfakorfez.supabase.co"
PAGE = 1000


def _url():
    return (os.environ.get("SUPABASE_URL") or PUBLIC_URL).rstrip("/")


def _headers(key, extra=None):
    h = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):
        h["Authorization"] = f"Bearer {key}"
    if extra:
        h.update(extra)
    return h


def _default(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(type(o))


class Store:
    def __init__(self, key=None, session=None):
        self.key = key or os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_SECRET_KEY")
        if not self.key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE is not set")
        self.base = _url() + "/rest/v1"
        self.http = session or requests.Session()

    def upsert(self, table, rows, conflict):
        rows = list(rows)
        for start in range(0, len(rows), PAGE):
            chunk = rows[start:start + PAGE]
            r = self.http.post(
                f"{self.base}/{table}",
                params={"on_conflict": conflict},
                headers=_headers(self.key, {"Prefer": "resolution=merge-duplicates,return=minimal"}),
                data=json.dumps(chunk, default=_default),
                timeout=60,
            )
            if r.status_code >= 300:
                raise RuntimeError(f"upsert {table} failed: {r.status_code} {r.text[:300]}")
        return len(rows)

    def upsert_prices(self, asset, points):
        return self.upsert("prices", [{"asset": asset, "day": d, "close": c} for d, c in points], "asset,day")

    def upsert_forecasts(self, asset, kind, forecasts, model):
        rows = [{
            "asset": asset,
            "kind": kind,
            "model": model,
            "made_on": f["made_on"],
            "price": f["price"],
            "trend": f["trend"],
            "trend_strength": f["trend_strength"],
            "vol_annual": f["vol_annual"],
            "lo": f["lo"],
            "hi": f["hi"],
            "coverage": f["coverage"],
            "target_on": f["target_on"],
        } for f in forecasts]
        return self.upsert("forecasts", rows, "asset,made_on,kind")

    def load_prices(self, asset):
        out = []
        offset = 0
        while True:
            r = self.http.get(
                f"{self.base}/prices",
                params={"select": "day,close", "asset": f"eq.{asset}", "order": "day.asc", "offset": offset, "limit": PAGE},
                headers=_headers(self.key),
                timeout=60,
            )
            r.raise_for_status()
            rows = r.json()
            out.extend((date.fromisoformat(x["day"]), float(x["close"])) for x in rows)
            if len(rows) < PAGE:
                return out
            offset += PAGE
