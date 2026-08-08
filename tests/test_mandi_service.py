"""
Tests for the mandi (Agmarknet / data.gov.in) price service.

The network layer is faked throughout — no API key and no HTTP call. What's
exercised is the part that can actually go wrong: tolerant field parsing,
outlier rejection, median selection, and the state -> national fallback.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import core.mandi_service as mandi
from core.mandi_service import (
    CROP_TO_COMMODITY,
    MAX_SANE_PRICE,
    MIN_RECORDS_FOR_CONFIDENCE,
    MIN_SANE_PRICE,
    _extract_modal_prices,
    _latest_arrival_date,
    _pick,
    _to_price,
    clear_cache,
    fetch_mandi_price,
    is_mandi_available,
)


@pytest.fixture(autouse=True)
def _clean():
    clear_cache()
    yield
    clear_cache()


def _record(modal, state="Punjab", date="2026-08-05", key="modal_price"):
    return {
        "state": state,
        "district": "Ludhiana",
        "market": "Khanna",
        "commodity": "Wheat",
        "arrival_date": date,
        "min_price": "2000",
        "max_price": "2600",
        key: str(modal),
    }


# ── Not configured ─────────────────────────────────────────────────────────────

def test_unavailable_without_api_key():
    assert is_mandi_available() is False


def test_fetch_returns_none_without_api_key():
    assert fetch_mandi_price("wheat", "Punjab") is None


def test_fetch_never_raises():
    try:
        fetch_mandi_price("wheat", "Punjab")
        fetch_mandi_price("nonexistent-crop")
        fetch_mandi_price("")
    except Exception as e:
        pytest.fail(f"fetch_mandi_price raised: {e}")


# ── Tolerant field reading ─────────────────────────────────────────────────────

def test_pick_is_case_insensitive():
    assert _pick({"Modal_Price": "2450"}, "modal_price") == "2450"


def test_pick_tries_alternate_spellings():
    assert _pick({"modal_x0020_price": "2450"}, "modal_price", "modal_x0020_price") == "2450"


def test_pick_skips_placeholder_values():
    assert _pick({"modal_price": "NA"}, "modal_price") is None
    assert _pick({"modal_price": ""}, "modal_price") is None


def test_extract_handles_mixed_key_casing():
    records = [_record(2400), _record(2500, key="Modal_Price")]
    assert sorted(_extract_modal_prices(records)) == [2400.0, 2500.0]


def test_price_parsing_strips_thousands_separator():
    assert _to_price("2,450") == 2450.0


def test_absurd_prices_are_rejected():
    assert _to_price(str(MIN_SANE_PRICE - 1)) is None
    assert _to_price(str(MAX_SANE_PRICE + 1)) is None
    assert _to_price("not a number") is None


def test_latest_arrival_date_picked():
    records = [_record(2400, date="2026-08-01"), _record(2450, date="2026-08-05")]
    assert _latest_arrival_date(records) == "2026-08-05"


# ── Aggregation ────────────────────────────────────────────────────────────────

def _stub(monkeypatch, by_scope):
    """by_scope: {"state": [...records...], "national": [...]}."""
    monkeypatch.setattr(mandi, "_get_api_key", lambda: "test-key")

    def fake_request(commodity, state):
        return by_scope.get("state" if state else "national", [])

    monkeypatch.setattr(mandi, "_request", fake_request)


def test_uses_median_not_mean(monkeypatch):
    # One wild outlier must not drag the figure up.
    prices = [2400, 2450, 2500, 99000]
    _stub(monkeypatch, {"state": [_record(p) for p in prices]})
    result = fetch_mandi_price("wheat", "Punjab")
    assert result["price_per_quintal"] == 2475     # median of the four
    assert result["price_per_quintal"] < 3000      # mean would be ~26,600


def test_result_shape_and_provenance(monkeypatch):
    _stub(monkeypatch, {"state": [_record(2400), _record(2450), _record(2500)]})
    result = fetch_mandi_price("wheat", "Punjab")
    assert result["source"] == "live"
    assert result["price_type"] == "market"
    assert result["scope"] == "state"
    assert result["sample_size"] == 3
    assert result["updated_at"] == "2026-08-05"


def test_thin_state_data_falls_back_to_national(monkeypatch):
    _stub(monkeypatch, {
        "state": [_record(2400)],                                  # below threshold
        "national": [_record(2200), _record(2250), _record(2300)],
    })
    result = fetch_mandi_price("wheat", "Punjab")
    assert result["scope"] == "national"
    assert result["price_per_quintal"] == 2250


def test_returns_none_when_everything_is_thin(monkeypatch):
    _stub(monkeypatch, {"state": [_record(2400)], "national": [_record(2200)]})
    assert fetch_mandi_price("wheat", "Punjab") is None


def test_outliers_can_starve_a_result(monkeypatch):
    """Records that are all junk must not produce a confident price."""
    _stub(monkeypatch, {"state": [_record(5) for _ in range(10)]})
    assert fetch_mandi_price("wheat", "Punjab") is None


def test_unknown_crop_returns_none(monkeypatch):
    _stub(monkeypatch, {"state": [_record(2400)] * 5})
    assert fetch_mandi_price("dragonfruit", "Punjab") is None


def test_result_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(mandi, "_get_api_key", lambda: "test-key")

    def counting_request(commodity, state):
        calls.append(commodity)
        return [_record(2400), _record(2450), _record(2500)]

    monkeypatch.setattr(mandi, "_request", counting_request)

    fetch_mandi_price("wheat", "Punjab")
    fetch_mandi_price("wheat", "Punjab")
    assert len(calls) == 1


def test_request_swallows_network_errors(monkeypatch):
    monkeypatch.setattr(mandi, "_get_api_key", lambda: "test-key")

    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(mandi.requests, "get", boom)
    assert mandi._request("Wheat", "Punjab") == []


# ── Crop mapping ───────────────────────────────────────────────────────────────

def test_every_app_crop_has_a_commodity_mapping():
    """A crop the app offers but Agmarknet can't be asked about would silently
    never get a live price."""
    from core.crop_data import list_crop_keys
    missing = [k for k in list_crop_keys() if k not in CROP_TO_COMMODITY]
    assert not missing, f"crops with no Agmarknet mapping: {missing}"


def test_price_service_tier1_delegates_here(monkeypatch):
    """resolve_price must actually surface a live mandi price when available."""
    import core.price_service as price_service

    monkeypatch.setattr(
        price_service, "_fetch_from_live_api",
        lambda crop, state=None: {
            "price_per_quintal": 2475, "price_type": "market",
            "source": "live", "updated_at": "2026-08-05",
        },
    )
    result = price_service.resolve_price("wheat", "Punjab")
    assert result["source"] == "live"
    assert result["price_per_quintal"] == 2475
