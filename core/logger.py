"""
Usage Event Logger — V3 with persistent Google Sheets backend
=============================================================
Primary:  POST to Google Apps Script Web App → appends row to Google Sheet
Fallback: Write to data/usage_log.jsonl (local/session only on Streamlit Cloud)

To activate persistent logging:
  Add to Streamlit Cloud Secrets:
    [logger]
    sheet_url = "https://script.google.com/macros/s/YOUR_ID/exec"

If secret is missing or POST fails, falls back to local file silently.
The app never crashes due to a logging failure.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "usage_log.jsonl")


def _get_sheet_url() -> Optional[str]:
    """Read Google Apps Script URL from Streamlit secrets. Returns None if not set."""
    try:
        import streamlit as st
        url = st.secrets.get("logger", {}).get("sheet_url", "")
        return url if url and url.startswith("https://") else None
    except Exception:
        return None


def _post_to_sheet(event: dict) -> bool:
    """POST event to Google Sheets via Apps Script. Returns True on success."""
    try:
        import requests
        url = _get_sheet_url()
        if not url:
            return False
        resp = requests.post(
            url,
            json=event,
            timeout=5,
            headers={"Content-Type": "application/json"},
        )
        return resp.status_code == 200
    except Exception:
        return False


def _write_to_file(event: dict) -> None:
    """Fallback: write to local jsonl file."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
    Log one recommendation event.
    Tries Google Sheets first. Falls back to local file.
    Never raises — logging must never crash the app.
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
        # Try persistent sheet first
        posted = _post_to_sheet(event)
        # Always write local file too (session-level backup)
        _write_to_file(event)
    except Exception:
        pass


def load_log_events(max_rows: int = 5000) -> list:
    """Load from local file for dashboard. Returns [] if file missing."""
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
    """Aggregate summary for dashboard."""
    events = load_log_events()
    if not events:
        return {"total": 0, "crops": {}, "states": {}, "risk_count": 0,
                "risk_pct": 0, "avg_margin": 0}
    crops, states = {}, {}
    risk_count, margins = 0, []
    for e in events:
        crops[e.get("crop", "?")] = crops.get(e.get("crop", "?"), 0) + 1
        states[e.get("state", "?")] = states.get(e.get("state", "?"), 0) + 1
        if e.get("risk_flag"):
            risk_count += 1
        if e.get("net_margin") is not None:
            margins.append(e["net_margin"])
    return {
        "total":      len(events),
        "crops":      dict(sorted(crops.items(), key=lambda x: x[1], reverse=True)),
        "states":     dict(sorted(states.items(), key=lambda x: x[1], reverse=True)),
        "risk_count": risk_count,
        "risk_pct":   round(risk_count / len(events) * 100, 1),
        "avg_margin": round(sum(margins) / len(margins)) if margins else 0,
    }
