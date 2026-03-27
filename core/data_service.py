"""
Data Service — Portfolio Data Provider
========================================
Tier 1: Real database query (stub — returns None until DB is connected)
Tier 2: Real usage log data (from logger.py)
Tier 3: Synthetic/simulated data for demonstration

Used exclusively by the internal dashboard (pages/4_Dashboard.py).
Disclaimer: When synthetic data is active, dashboard shows a clear notice.
"""

import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from core.logger import load_log_events, get_log_summary


# ── Tier 1: Database stub ──────────────────────────────────────────────────────

def _fetch_from_database() -> Optional[List[Dict[str, Any]]]:
    """
    STUB — connect your database here when ready.

    Expected return: list of event dicts matching the same schema
    as usage_log.jsonl entries.

    Until connected: return None so resolver falls through.
    """
    return None


# ── Tier 2: Real log data ──────────────────────────────────────────────────────

def _fetch_from_log() -> Optional[List[Dict[str, Any]]]:
    events = load_log_events()
    return events if events else None


# ── Tier 3: Synthetic data generator ──────────────────────────────────────────

SYNTHETIC_CROPS = ["rice", "wheat", "cotton", "maize", "soybean",
                   "groundnut", "mustard", "sugarcane", "onion", "potato"]
SYNTHETIC_STATES = ["Maharashtra", "Punjab", "Uttar Pradesh", "Madhya Pradesh",
                    "Karnataka", "Andhra Pradesh", "Gujarat", "Rajasthan",
                    "West Bengal", "Bihar", "Telangana", "Haryana"]
SYNTHETIC_SEASONS = ["kharif", "rabi", "annual"]
SYNTHETIC_SOILS = ["black", "alluvial", "red_laterite", "red_loamy", "arid_sandy"]
SYNTHETIC_IRRIGATION = ["borewell", "canal", "rainfed", "drip"]

CROP_MARGIN_RANGES = {
    "rice":      (8000, 35000),
    "wheat":     (12000, 42000),
    "cotton":    (6000, 45000),
    "maize":     (10000, 32000),
    "soybean":   (8000, 28000),
    "groundnut": (5000, 40000),
    "mustard":   (15000, 50000),
    "sugarcane": (20000, 80000),
    "onion":     (-5000, 60000),
    "potato":    (-10000, 45000),
}


def _generate_synthetic_events(n: int = 150) -> List[Dict[str, Any]]:
    random.seed(42)  # Reproducible synthetic data
    events = []
    base_date = datetime.now() - timedelta(days=90)

    for i in range(n):
        crop = random.choice(SYNTHETIC_CROPS)
        state = random.choice(SYNTHETIC_STATES)
        margin_range = CROP_MARGIN_RANGES.get(crop, (5000, 40000))
        acreage = round(random.uniform(1.0, 8.0), 1)
        net_margin = random.randint(*margin_range)
        gross_rev = net_margin + random.randint(15000, 80000)
        ts = base_date + timedelta(days=random.randint(0, 90),
                                   hours=random.randint(0, 23))
        events.append({
            "ts":             ts.isoformat(),
            "crop":           crop,
            "state":          state,
            "season":         random.choice(SYNTHETIC_SEASONS),
            "acreage":        acreage,
            "gross_revenue":  gross_rev,
            "total_cost":     gross_rev - net_margin,
            "net_margin":     net_margin,
            "margin_per_acre":round(net_margin / acreage),
            "risk_flag":      net_margin / acreage < 5000,
            "price_source":   random.choice(["default", "cache", "default", "default"]),
            "soil_code":      random.choice(SYNTHETIC_SOILS),
            "climate_zone":   "Tropical",
            "llm_used":       random.random() > 0.7,
            "irrigation":     random.choice(SYNTHETIC_IRRIGATION),
        })

    return sorted(events, key=lambda x: x["ts"], reverse=True)


# ── Public resolver ────────────────────────────────────────────────────────────

def get_portfolio_data() -> Dict[str, Any]:
    """
    Returns portfolio data for the internal dashboard.
    Also returns data_source string so dashboard can show correct disclaimer.
    """
    # Tier 1
    events = _fetch_from_database()
    if events:
        return {"events": events, "source": "database", "count": len(events)}

    # Tier 2
    events = _fetch_from_log()
    if events and len(events) >= 5:
        summary = get_log_summary()
        return {"events": events, "source": "live_log",
                "count": len(events), "summary": summary}

    # Tier 3 — synthetic
    events = _generate_synthetic_events(150)
    return {"events": events, "source": "synthetic", "count": len(events)}


def compute_risk_segments(events: List[Dict]) -> Dict[str, Any]:
    """Compute risk segmentation from event list."""
    if not events:
        return {"low": 0, "medium": 0, "high": 0, "total": 0}

    low = medium = high = 0
    for e in events:
        mpa = e.get("margin_per_acre", e.get("net_margin", 0))
        if mpa >= 10000:
            low += 1
        elif mpa >= 5000:
            medium += 1
        else:
            high += 1

    total = len(events)
    return {
        "low":        low,
        "medium":     medium,
        "high":       high,
        "total":      total,
        "low_pct":    round(low / total * 100, 1),
        "medium_pct": round(medium / total * 100, 1),
        "high_pct":   round(high / total * 100, 1),
    }
