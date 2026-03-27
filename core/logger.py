"""
Usage Event Logger
==================
Writes structured usage events to data/usage_log.jsonl (one JSON object per line).
No personal data is stored — only farm economics and app usage patterns.

This is the instrumentation layer. It enables:
- Operational proof (real usage data)
- Dashboard analytics (crop/state/margin distributions)
- Future ML training data

Privacy: no farmer name, no exact location, no contact info.
Only: crop, state, acreage, margin, risk flag, price source, timestamp.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "usage_log.jsonl")


def log_recommendation_event(
    crop: str,
    state: str,
    season: str,
    acreage: float,
    gross_revenue: float,
    total_cost: float,
    net_margin: float,
    risk_flag: bool,
    price_source: str,
    soil_code: str = "unknown",
    climate_zone: str = "unknown",
    llm_used: bool = False,
    irrigation_type: str = "unknown",
) -> None:
    """
    Log a single recommendation event.
    Called once per successful recommendation generation.
    Silent on failure — logging must never crash the app.
    """
    try:
        event = {
            "ts":             datetime.now(timezone.utc).isoformat(),
            "crop":           crop,
            "state":          state,
            "season":         season,
            "acreage":        round(acreage, 1),
            "gross_revenue":  int(gross_revenue),
            "total_cost":     int(total_cost),
            "net_margin":     int(net_margin),
            "margin_per_acre": round(net_margin / acreage, 0) if acreage > 0 else 0,
            "risk_flag":      risk_flag,
            "price_source":   price_source,
            "soil_code":      soil_code,
            "climate_zone":   climate_zone,
            "llm_used":       llm_used,
            "irrigation":     irrigation_type,
        }
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never propagate logging errors to the user


def load_log_events(max_rows: int = 5000) -> list:
    """
    Load log events for dashboard display.
    Returns list of dicts, most recent first.
    Returns empty list if log file doesn't exist yet.
    """
    if not os.path.exists(LOG_FILE):
        return []
    try:
        events = []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        continue
        return list(reversed(events[-max_rows:]))
    except Exception:
        return []


def get_log_summary() -> dict:
    """
    Returns aggregate summary of log events.
    Used by the internal dashboard.
    """
    events = load_log_events()
    if not events:
        return {"total": 0, "crops": {}, "states": {}, "risk_count": 0}

    crops = {}
    states = {}
    risk_count = 0
    margins = []

    for e in events:
        crops[e.get("crop", "unknown")] = crops.get(e.get("crop", "unknown"), 0) + 1
        states[e.get("state", "unknown")] = states.get(e.get("state", "unknown"), 0) + 1
        if e.get("risk_flag"):
            risk_count += 1
        if e.get("net_margin") is not None:
            margins.append(e["net_margin"])

    return {
        "total":       len(events),
        "crops":       dict(sorted(crops.items(), key=lambda x: x[1], reverse=True)),
        "states":      dict(sorted(states.items(), key=lambda x: x[1], reverse=True)),
        "risk_count":  risk_count,
        "risk_pct":    round(risk_count / len(events) * 100, 1) if events else 0,
        "avg_margin":  round(sum(margins) / len(margins)) if margins else 0,
    }
