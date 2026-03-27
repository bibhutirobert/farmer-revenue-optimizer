"""
Price Service — Three-Tier Resolver
====================================
Tier 1: Live API (stub — returns None until real endpoint is connected)
Tier 2: Admin-editable cache file (data/price_cache.json)
Tier 3: Hardcoded default from crops.json (always available)

To activate Tier 1: fill in _fetch_from_live_api() with your API call.
To refresh Tier 2: edit data/price_cache.json and update updated_at date.
Nothing else in the codebase needs to change.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "price_cache.json")
CACHE_MAX_AGE_DAYS = 30  # treat cache as stale if older than this


# ── Tier 1: Live API stub ──────────────────────────────────────────────────────

def _fetch_from_live_api(crop: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    STUB — connect your live price API here.

    Expected return format:
    {
        "price_per_quintal": 2300,
        "price_type": "msp",
        "source": "live",
        "updated_at": "2024-03-15"
    }

    Candidate APIs to connect:
    - Agmarknet (https://agmarknet.gov.in/) — mandi prices
    - data.gov.in commodity price API
    - eNAM (National Agriculture Market) API

    Until connected: return None so resolver falls through to Tier 2.
    """
    return None  # Replace with actual API call when ready


# ── Tier 2: Cache file ─────────────────────────────────────────────────────────

def _load_cache() -> Dict[str, Any]:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _is_cache_fresh(entry: Dict[str, Any]) -> bool:
    try:
        updated = datetime.strptime(entry.get("updated_at", "2000-01-01"), "%Y-%m-%d")
        return (datetime.now() - updated).days <= CACHE_MAX_AGE_DAYS
    except Exception:
        return False


def _fetch_from_cache(crop: str) -> Optional[Dict[str, Any]]:
    cache = _load_cache()
    prices = cache.get("prices", {})
    entry = prices.get(crop)
    if entry and _is_cache_fresh(entry):
        return {
            "price_per_quintal": entry["price_per_quintal"],
            "price_type":        entry.get("price_type", "market"),
            "source":            "cache",
            "updated_at":        entry.get("updated_at", "unknown"),
        }
    return None


# ── Tier 3: Hardcoded default ──────────────────────────────────────────────────

def _get_default_price(crop: str) -> Dict[str, Any]:
    """Always returns a value — the hardcoded fallback from crops.json."""
    from core.crop_data import get_crop
    crop_data = get_crop(crop)
    if crop_data:
        return {
            "price_per_quintal": crop_data["price_per_quintal"],
            "price_type":        crop_data.get("price_type", "default"),
            "source":            "default",
            "updated_at":        "hardcoded",
        }
    # Absolute last resort
    return {
        "price_per_quintal": 2000,
        "price_type":        "default",
        "source":            "default",
        "updated_at":        "hardcoded",
    }


# ── Public resolver function ───────────────────────────────────────────────────

def resolve_price(crop: str, state: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point. Returns price dict with source metadata.

    Return format:
    {
        "price_per_quintal": int,
        "price_type": str,        # "msp" | "frp" | "market" | "default"
        "source": str,            # "live" | "cache" | "default"
        "updated_at": str,        # ISO date string or "hardcoded"
    }
    """
    # Tier 1
    result = _fetch_from_live_api(crop, state)
    if result:
        result["source"] = "live"
        return result

    # Tier 2
    result = _fetch_from_cache(crop)
    if result:
        return result

    # Tier 3 — always works
    return _get_default_price(crop)


def get_price_label(source: str, updated_at: str, lang: str = "en") -> str:
    """Human-readable label for displaying price provenance in reports."""
    if source == "live":
        label_en = f"Live market price (as of {updated_at})"
        label_hi = f"लाइव बाजार भाव ({updated_at} तक)"
    elif source == "cache":
        label_en = f"Cached market/MSP price (updated {updated_at})"
        label_hi = f"कैश्ड बाजार/MSP भाव ({updated_at} को अपडेट)"
    else:
        label_en = "Reference price (MSP/FRP 2023-24)"
        label_hi = "संदर्भ भाव (MSP/FRP 2023-24)"

    return label_hi if lang == "hi" else label_en
