import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.price_service import resolve_price, get_price_label, _get_default_price, _fetch_from_live_api


def test_resolve_price_returns_dict():
    result = resolve_price("wheat")
    assert isinstance(result, dict)
    assert "price_per_quintal" in result
    assert "source" in result
    assert "price_type" in result
    assert "updated_at" in result


def test_resolve_price_positive():
    for crop in ["rice", "wheat", "cotton", "mustard", "bajra"]:
        result = resolve_price(crop)
        assert result["price_per_quintal"] > 0, f"Price for {crop} should be positive"


def test_resolve_price_source_is_valid():
    result = resolve_price("rice")
    assert result["source"] in ("live", "cache", "default")


def test_live_api_stub_returns_none():
    """Tier 1 must return None until a real API is connected."""
    assert _fetch_from_live_api("wheat") is None
    assert _fetch_from_live_api("rice", "Punjab") is None


def test_default_price_always_works():
    result = _get_default_price("sugarcane")
    assert result["price_per_quintal"] == 340
    assert result["source"] == "default"


def test_default_price_unknown_crop():
    result = _get_default_price("nonexistent_crop_xyz")
    assert result["price_per_quintal"] == 2000
    assert result["source"] == "default"


def test_price_label_live():
    label = get_price_label("live", "2024-03-15", "en")
    assert "Live" in label or "live" in label.lower()


def test_price_label_cache():
    label = get_price_label("cache", "2024-02-01", "en")
    assert "2024-02-01" in label


def test_price_label_default():
    label = get_price_label("default", "hardcoded", "en")
    assert "Reference" in label or "2023" in label


def test_price_label_hindi():
    label = get_price_label("cache", "2024-03-01", "hi")
    assert label  # Must return something non-empty
