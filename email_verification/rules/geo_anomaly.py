from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..context import RuleContext
from ..rule_engine import Rule


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Simple haversine calculation
    from math import radians, cos, sin, asin, sqrt

    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


class GeoAnomalyRule(Rule):
    name = "GeoAnomalyRule"
    priority = 50

    def evaluate(self, event: Dict[str, Any], context: RuleContext) -> None:
        if event.get("type") != "AuthVerificationRequested":
            return
        user_id = event.get("user_id")
        geo = event.get("geo")  # expected like {"lat": ..., "lon": ..., "city": "...", "country": "..."}
        ts_iso = event.get("timestamp")
        if not (user_id and geo and ts_iso and isinstance(geo, dict) and "lat" in geo and "lon" in geo):
            return

        # Maintain per-user recent locations with timestamps (simple in-memory KV for demo)
        key = f"geo_hist:{user_id}"
        hist: List[Dict[str, Any]] = context.kv.get(key) or []

        # Warmup period: require initial 10 events
        if len(hist) >= 1:
            last = hist[-1]
            last_geo = last.get("geo", {})
            last_ts = datetime.fromisoformat(str(last.get("ts")).replace("Z", "+00:00"))
            cur_ts = datetime.fromisoformat(str(ts_iso).replace("Z", "+00:00"))
            hours = (cur_ts - last_ts).total_seconds() / 3600.0
            try:
                dist_km = _haversine_km(float(last_geo["lat"]), float(last_geo["lon"]), float(geo["lat"]), float(geo["lon"]))
            except Exception:
                dist_km = 0.0
            speed_kmh = dist_km / max(hours, 1e-6)
            # Flag impossible travel: > 1000 km/h
            if len(hist) >= 10 and speed_kmh > 1000.0:
                context.alert(
                    severity="medium",
                    rule=self.name,
                    message="Geo anomaly: impossible travel detected",
                    user_id=user_id,
                    speed_kmh=round(speed_kmh, 1),
                    distance_km=round(dist_km, 1),
                    hours=round(hours, 2),
                )

        # Append current
        hist.append({"geo": geo, "ts": ts_iso})
        # Keep only last 100 entries to bound memory
        context.kv.set(key, hist[-100:])
