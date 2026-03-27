"""
Soil Service — Two-Tier Resolver
==================================
Tier 1: Real-time soil API (stub — returns None until connected)
Tier 2: State-level soil + climate mapping from data/soil_climate.json

The LLM (llm_service.py) receives the resolved soil/climate data as
structured input — it never guesses geospatial facts directly.
"""

import json
import os
from typing import Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SOIL_CLIMATE_FILE = os.path.join(DATA_DIR, "soil_climate.json")

_CACHE: Optional[Dict] = None


def _load_soil_climate() -> Dict:
    global _CACHE
    if _CACHE is None:
        with open(SOIL_CLIMATE_FILE, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


# ── Tier 1: Real soil API stub ─────────────────────────────────────────────────

def _fetch_from_soil_api(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """
    STUB — connect field-level soil API here.

    Candidate sources:
    - ISRO Bhuvan NBSS&LUP soil layer (requires authentication)
    - FAO SoilGrids REST API (https://rest.isric.org/) — global, no auth
    - OpenLandMap soil API

    FAO SoilGrids example endpoint (when ready):
        GET https://rest.isric.org/soilgrids/v2.0/properties/query
        params: lon={lng}&lat={lat}&property=phh2o&depth=0-30cm&value=mean

    Until connected: return None so resolver falls through to Tier 2.
    """
    return None


# ── Tier 2: State-level mapping ────────────────────────────────────────────────

def _get_from_state_map(state: str) -> Optional[Dict[str, Any]]:
    data = _load_soil_climate()
    states = data.get("states", {})
    entry = states.get(state)
    if not entry:
        return None

    soil_code = entry.get("soil_code", "alluvial")
    soil_descs = data.get("soil_descriptions", {})
    soil_desc = soil_descs.get(soil_code, {})

    return {
        "soil_code":       soil_code,
        "soil_name_en":    soil_desc.get("name_en", entry.get("dominant_soil", "Unknown")),
        "soil_name_hi":    soil_desc.get("name_hi", entry.get("dominant_soil", "अज्ञात")),
        "soil_desc_en":    soil_desc.get("description_en", ""),
        "soil_desc_hi":    soil_desc.get("description_hi", ""),
        "climate_zone":    entry.get("climate_zone", "Tropical"),
        "rainfall_cat":    entry.get("rainfall_category", "medium"),
        "temp_zone":       entry.get("temp_zone", "warm"),
        "primary_kharif":  entry.get("primary_kharif", []),
        "primary_rabi":    entry.get("primary_rabi", []),
        "agro_notes_en":   entry.get("agro_notes_en", ""),
        "agro_notes_hi":   entry.get("agro_notes_hi", ""),
        "source":          "state_map",
    }


# ── Public resolver ────────────────────────────────────────────────────────────

def resolve_soil_climate(
    state: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Returns soil + climate data for a given location.

    Tries Tier 1 (real API) first if lat/lng are provided.
    Falls back to Tier 2 (state-level map) which always works.
    """
    if lat is not None and lng is not None:
        result = _fetch_from_soil_api(lat, lng)
        if result:
            return result

    result = _get_from_state_map(state)
    if result:
        return result

    # Absolute fallback — generic alluvial
    return {
        "soil_code":      "alluvial",
        "soil_name_en":   "Alluvial Soil",
        "soil_name_hi":   "जलोढ़ मिट्टी",
        "soil_desc_en":   "Fertile soil deposited by rivers. Suitable for most crops.",
        "soil_desc_hi":   "नदियों द्वारा जमा उपजाऊ मिट्टी। अधिकांश फसलों के लिए उपयुक्त।",
        "climate_zone":   "Tropical",
        "rainfall_cat":   "medium",
        "temp_zone":      "warm",
        "primary_kharif": ["rice", "maize"],
        "primary_rabi":   ["wheat", "mustard"],
        "agro_notes_en":  "",
        "agro_notes_hi":  "",
        "source":         "fallback",
    }


def get_ranked_crops(
    soil_code: str,
    season: str,
    climate_zone: str,
    state: str,
) -> list:
    """
    Returns ranked list of up to 3 recommended crop keys for the given
    soil + season + climate combination.
    Used to pre-select crops on the farm details form.
    """
    data = _load_soil_climate()
    state_entry = data.get("states", {}).get(state, {})

    # Get season-appropriate crops from state data
    if season == "kharif" or season == "zaid":
        candidates = state_entry.get("primary_kharif", [])
    elif season == "rabi":
        candidates = state_entry.get("primary_rabi", [])
    else:  # annual
        candidates = state_entry.get("primary_kharif", []) + state_entry.get("primary_rabi", [])

    # Soil-based ranking boost
    SOIL_CROP_FIT = {
        "alluvial":       ["rice", "wheat", "sugarcane", "potato", "maize"],
        "black":          ["cotton", "soybean", "sugarcane", "wheat", "onion"],
        "red_laterite":   ["groundnut", "jowar", "bajra", "maize", "cotton"],
        "red_loamy":      ["groundnut", "cotton", "maize", "jowar", "sugarcane"],
        "arid_sandy":     ["bajra", "jowar", "mustard", "groundnut"],
        "red_yellow":     ["rice", "maize", "soybean", "jowar"],
        "laterite":       ["rice", "sugarcane", "maize"],
        "forest_hill":    ["rice", "maize", "potato"],
        "mountain_forest":["maize", "wheat", "potato"],
        "red_black_mixed":["cotton", "rice", "soybean", "chilli"],
    }

    preferred = SOIL_CROP_FIT.get(soil_code, [])

    # Rank: crops that appear in both candidates and preferred come first
    ranked = [c for c in preferred if c in candidates]
    ranked += [c for c in candidates if c not in ranked]

    # Return top 3 that exist in our dataset
    from core.crop_data import list_crop_keys
    valid_keys = list_crop_keys()
    return [c for c in ranked if c in valid_keys][:3]
