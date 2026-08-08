"""
Weather Utils — Open-Meteo forecast for a confirmed field.
==========================================================

Open-Meteo is free for non-commercial use and needs **no API key**, so this
works on a fresh deployment with nothing configured.

Same failure posture as price_service and llm_service: every entry point
returns None (or an empty list) on any network/parse problem. Weather is
advisory garnish — it must never take the advisory flow down with it.

Thresholds below are deliberately coarse rules of thumb for rain-fed Indian
smallholdings, not agronomic truth. They are constants so a domain expert can
retune them in one place.
"""

import time
from typing import Any, Dict, List, Optional

import requests

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 8
FORECAST_DAYS = 7

# Rules of thumb, millimetres over the forecast window.
DRY_SPELL_MM = 10.0        # below this, expect to irrigate
WET_WINDOW_MM = 50.0       # above this, soil moisture is likely adequate
WATERLOGGING_MM = 150.0    # above this, drainage becomes the concern
HEAVY_DAY_MM = 30.0        # a single day this wet blocks sowing/spraying

_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SECONDS = 3 * 60 * 60  # forecasts do not move fast enough to refetch


def _cache_key(lat: float, lng: float) -> str:
    # ~1 km grid — neighbouring fields share a forecast, which is correct here
    # and keeps us well clear of any rate limit.
    return f"{lat:.2f},{lng:.2f}"


def fetch_forecast(lat: float, lng: float, days: int = FORECAST_DAYS) -> Optional[Dict[str, Any]]:
    """
    Daily forecast for a point. Returns None if unavailable — never raises.

    Shape: {"dates": [...], "rain_mm": [...], "temp_max": [...], "temp_min": [...]}
    """
    key = _cache_key(lat, lng)
    cached = _CACHE.get(key)
    if cached and (time.time() - cached["at"]) < _CACHE_TTL_SECONDS:
        return cached["value"]

    try:
        response = requests.get(
            API_URL,
            params={
                "latitude": lat,
                "longitude": lng,
                "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
                "forecast_days": days,
                "timezone": "auto",
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        daily = (response.json() or {}).get("daily") or {}
    except Exception:
        return None

    dates = daily.get("time") or []
    if not dates:
        return None

    def _floats(values: Any) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        for v in (values or []):
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                out.append(None)
        return out

    forecast = {
        "dates": list(dates),
        "rain_mm": _floats(daily.get("precipitation_sum")),
        "temp_max": _floats(daily.get("temperature_2m_max")),
        "temp_min": _floats(daily.get("temperature_2m_min")),
    }
    _CACHE[key] = {"at": time.time(), "value": forecast}
    return forecast


def total_rainfall(forecast: Optional[Dict[str, Any]]) -> Optional[float]:
    """Sum of forecast rainfall in mm, ignoring gaps. None if unusable."""
    if not forecast:
        return None
    values = [v for v in (forecast.get("rain_mm") or []) if v is not None]
    if not values:
        return None
    return round(sum(values), 1)


def heavy_rain_dates(forecast: Optional[Dict[str, Any]],
                     threshold_mm: float = HEAVY_DAY_MM) -> List[str]:
    """Dates whose forecast rain meets or exceeds the heavy-day threshold."""
    if not forecast:
        return []
    dates = forecast.get("dates") or []
    rain = forecast.get("rain_mm") or []
    return [
        date
        for date, mm in zip(dates, rain)
        if mm is not None and mm >= threshold_mm
    ]


def weather_tips(forecast: Optional[Dict[str, Any]], lang: str = "en") -> List[str]:
    """
    Farmer-facing guidance derived from the forecast.

    Empty list when there is no forecast — callers render nothing rather than
    an apology, which keeps the page clean when the API is unreachable.
    """
    total = total_rainfall(forecast)
    if total is None:
        return []

    hi = lang == "hi"
    days = len(forecast.get("dates") or [])
    tips: List[str] = []

    if hi:
        tips.append(f"अगले {days} दिनों में अनुमानित वर्षा: **{total} मिमी**")
    else:
        tips.append(f"Forecast rainfall over the next {days} days: **{total} mm**")

    if total < DRY_SPELL_MM:
        tips.append(
            "सूखा दौर — सिंचाई की योजना बनाएं, बुवाई के तुरंत बाद पानी दें।"
            if hi else
            "Dry spell ahead — plan irrigation, and water soon after sowing."
        )
    elif total >= WATERLOGGING_MM:
        tips.append(
            "बहुत अधिक वर्षा — जल निकासी नालियां साफ रखें, जलभराव से बचाएं।"
            if hi else
            "Very heavy rainfall — clear drainage channels and guard against waterlogging."
        )
    elif total >= WET_WINDOW_MM:
        tips.append(
            "पर्याप्त नमी की संभावना — सिंचाई टाल सकते हैं, लागत बचेगी।"
            if hi else
            "Soil moisture likely adequate — irrigation can probably wait, saving cost."
        )

    heavy = heavy_rain_dates(forecast)
    if heavy:
        shown = ", ".join(heavy[:3])
        tips.append(
            f"भारी वर्षा के दिन ({shown}) — छिड़काव और बुवाई से बचें।"
            if hi else
            f"Heavy rain expected ({shown}) — avoid spraying and sowing on those days."
        )

    return tips


def clear_cache() -> None:
    """Drop the in-process forecast cache (used by tests)."""
    _CACHE.clear()
