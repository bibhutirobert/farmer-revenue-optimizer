import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.soil_service import (
    resolve_soil_climate, get_ranked_crops, _fetch_from_soil_api, _get_from_state_map
)


def test_resolve_returns_dict():
    result = resolve_soil_climate("Maharashtra")
    assert isinstance(result, dict)


def test_resolve_required_keys():
    result = resolve_soil_climate("Punjab")
    for key in ("soil_code", "soil_name_en", "soil_name_hi", "climate_zone",
                "rainfall_cat", "temp_zone", "primary_kharif", "primary_rabi"):
        assert key in result, f"Missing key: {key}"


def test_all_28_states_resolve():
    states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    ]
    for state in states:
        result = resolve_soil_climate(state)
        assert result["soil_code"], f"{state} returned empty soil_code"
        assert result["climate_zone"], f"{state} returned empty climate_zone"


def test_black_soil_for_maharashtra():
    result = resolve_soil_climate("Maharashtra")
    assert result["soil_code"] == "black"


def test_alluvial_for_punjab():
    result = resolve_soil_climate("Punjab")
    assert result["soil_code"] == "alluvial"


def test_arid_for_rajasthan():
    result = resolve_soil_climate("Rajasthan")
    assert result["soil_code"] == "arid_sandy"


def test_fallback_on_unknown_state():
    result = resolve_soil_climate("Unknown State XYZ")
    assert result["soil_code"] == "alluvial"
    assert result["source"] == "fallback"


def test_soil_api_stub_returns_none():
    assert _fetch_from_soil_api(19.0, 72.8) is None


def test_state_map_returns_none_for_unknown():
    result = _get_from_state_map("Nonexistent State")
    assert result is None


def test_get_ranked_crops_returns_list():
    crops = get_ranked_crops("black", "kharif", "Tropical Semi-Arid", "Maharashtra")
    assert isinstance(crops, list)
    assert len(crops) <= 3


def test_ranked_crops_contain_valid_keys():
    from core.crop_data import list_crop_keys
    valid = list_crop_keys()
    crops = get_ranked_crops("alluvial", "rabi", "Sub-Tropical", "Punjab")
    for c in crops:
        assert c in valid, f"{c} is not a valid crop key"


def test_ranked_crops_black_soil_kharif():
    crops = get_ranked_crops("black", "kharif", "Tropical Semi-Arid", "Maharashtra")
    assert len(crops) > 0
    # Cotton should feature strongly for black soil kharif
    assert "cotton" in crops or "soybean" in crops


def test_ranked_crops_alluvial_rabi():
    crops = get_ranked_crops("alluvial", "rabi", "Semi-Arid", "Punjab")
    assert len(crops) > 0
    assert "wheat" in crops


def test_ranked_crops_max_three():
    for soil in ["black", "alluvial", "red_laterite", "arid_sandy"]:
        crops = get_ranked_crops(soil, "kharif", "Tropical", "Maharashtra")
        assert len(crops) <= 3
