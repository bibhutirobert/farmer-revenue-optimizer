"""
Mandi Price Service — data.gov.in / Agmarknet
=============================================

Live daily mandi (market) prices, used as Tier 1 of core/price_service.py.

Source: the Government of India open-data resource "Current Daily Price of
Various Commodities from Various Markets (Mandi)" on data.gov.in, which
republishes Agmarknet. Needs a **free** API key from
https://data.gov.in — register, then put it in secrets:

    [data_gov]
    api_key = "..."

Without a key every entry point returns None and price_service falls through
to its cache and hardcoded MSP tiers exactly as before. Same posture as the
rest of the codebase: a missing key or a bad day at the API must never break
the advisory.

WHY MODAL PRICE, AND WHY THE MEDIAN
  Each record carries min / max / modal price for one commodity in one mandi
  on one day. Modal is the most-traded price, so it is the best single
  estimate of what a farmer actually gets. We take the *median* modal price
  across mandis rather than the mean because mandi data carries occasional
  wild outliers (unit errors, premium varieties), and one bad record should
  not move a farmer's revenue projection.

A NOTE ON WHAT THIS CHANGES
  Switching from MSP to live mandi price makes projections more realistic,
  but mandi prices sit *below* MSP for many crops in glut season. That is a
  real signal, not a bug — the advisory is more honest with it than without.
"""

import statistics
import time
from typing import Any, Dict, List, Optional

import requests

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
TIMEOUT_SECONDS = 10
RECORD_LIMIT = 500

# Below/above these (rupees per quintal) a record is treated as junk rather
# than signal — protects against unit errors and stray decimal points.
MIN_SANE_PRICE = 100
MAX_SANE_PRICE = 100_000
MIN_RECORDS_FOR_CONFIDENCE = 3

_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60  # mandi data updates daily; 6h is plenty

# App crop keys -> Agmarknet commodity names. Agmarknet's naming is its own
# thing ("Paddy(Dhan)(Common)"), so this map is required, not cosmetic.
# Several crops list alternates because naming varies by state feed.
CROP_TO_COMMODITY: Dict[str, List[str]] = {
    "rice":      ["Paddy(Dhan)(Common)", "Rice", "Paddy(Dhan)(Basmati)"],
    "wheat":     ["Wheat"],
    "cotton":    ["Cotton"],
    "sugarcane": ["Sugarcane"],
    "maize":     ["Maize"],
    "soybean":   ["Soyabean", "Soybean"],
    "groundnut": ["Groundnut", "Groundnut (Split)"],
    "mustard":   ["Mustard", "Rape & Mustard Seed"],
    "jowar":     ["Jowar(Sorghum)", "Jowar"],
    "bajra":     ["Bajra(Pearl Millet/Cumbu)", "Bajra"],
    "onion":     ["Onion"],
    "tomato":    ["Tomato"],
    "potato":    ["Potato"],
    "turmeric":  ["Turmeric"],
    "chilli":    ["Chilli Red", "Green Chilli", "Dry Chillies"],
}


def _get_api_key() -> Optional[str]:
    try:
        import streamlit as st
        key = st.secrets.get("data_gov", {}).get("api_key", "")
        return key.strip() or None
    except Exception:
        return None


def is_mandi_available() -> bool:
    """True when a data.gov.in API key is configured."""
    return _get_api_key() is not None


def _pick(record: Dict[str, Any], *names: str) -> Optional[str]:
    """
    Read a field tolerantly.

    The data.gov.in feed has changed field casing over time
    (`modal_price` vs `Modal_Price`), so match case-insensitively across
    a few known spellings instead of trusting one.
    """
    lowered = {str(k).strip().lower(): v for k, v in record.items()}
    for name in names:
        value = lowered.get(name.strip().lower())
        if value not in (None, "", "NA", "-"):
            return str(value)
    return None


def _to_price(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    try:
        value = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not (MIN_SANE_PRICE <= value <= MAX_SANE_PRICE):
        return None
    return value


def _extract_modal_prices(records: List[Dict[str, Any]]) -> List[float]:
    prices = []
    for record in records or []:
        price = _to_price(_pick(record, "modal_price", "modal_x0020_price", "modalprice"))
        if price is not None:
            prices.append(price)
    return prices


def _latest_arrival_date(records: List[Dict[str, Any]]) -> Optional[str]:
    dates = [
        _pick(r, "arrival_date", "arrival_x0020_date", "arrivaldate")
        for r in records or []
    ]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def _request(commodity: str, state: Optional[str]) -> List[Dict[str, Any]]:
    """One API call. Returns [] on any failure — never raises."""
    api_key = _get_api_key()
    if not api_key:
        return []

    params = {
        "api-key": api_key,
        "format": "json",
        "limit": RECORD_LIMIT,
        "filters[commodity]": commodity,
    }
    if state:
        params["filters[state]"] = state

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return (response.json() or {}).get("records") or []
    except Exception:
        return []


def fetch_mandi_price(crop: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Median modal mandi price for a crop, in rupees per quintal.

    Prefers mandis in the farmer's own state; falls back to a national figure
    when the state feed is thin, since a distant real price beats a stale
    hardcoded one. Returns None when unavailable, so callers fall through.

    Shape:
      {"price_per_quintal": int, "price_type": "market",
       "source": "live", "updated_at": "YYYY-MM-DD",
       "sample_size": int, "scope": "state"|"national"}
    """
    if not is_mandi_available():
        return None

    commodities = CROP_TO_COMMODITY.get(crop.strip().lower())
    if not commodities:
        return None

    cache_key = f"{crop.lower()}|{(state or '').lower()}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached["at"]) < _CACHE_TTL_SECONDS:
        return cached["value"]

    result = None
    # State first, then national — and try each commodity alias in turn.
    for scope, scope_state in (("state", state), ("national", None)):
        if scope == "state" and not state:
            continue
        for commodity in commodities:
            records = _request(commodity, scope_state)
            prices = _extract_modal_prices(records)
            if len(prices) >= MIN_RECORDS_FOR_CONFIDENCE:
                result = {
                    "price_per_quintal": int(round(statistics.median(prices))),
                    "price_type": "market",
                    "source": "live",
                    "updated_at": _latest_arrival_date(records) or "unknown",
                    "sample_size": len(prices),
                    "scope": scope,
                }
                break
        if result:
            break

    _CACHE[cache_key] = {"at": time.time(), "value": result}
    return result


def clear_cache() -> None:
    """Drop the in-process price cache (used by tests)."""
    _CACHE.clear()
