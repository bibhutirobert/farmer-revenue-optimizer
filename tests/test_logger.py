"""
Tests for the usage event logger.
Uses a temporary log file to avoid polluting data/usage_log.jsonl.
"""
import pytest
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import core.logger as logger_module
from core.logger import log_recommendation_event, load_log_events, get_log_summary


@pytest.fixture(autouse=True)
def temp_log_file(tmp_path, monkeypatch):
    """Redirect log writes to a temp file for each test."""
    temp_log = str(tmp_path / "test_usage_log.jsonl")
    monkeypatch.setattr(logger_module, "LOG_FILE", temp_log)
    yield temp_log


def test_log_creates_file(temp_log_file):
    log_recommendation_event(
        crop="wheat", state="Punjab", season="rabi",
        acreage=2.0, gross_revenue=50000, total_cost=25000,
        net_margin=25000, risk_flag=False, price_source="default",
    )
    assert os.path.exists(temp_log_file)


def test_log_writes_valid_json(temp_log_file):
    log_recommendation_event(
        crop="rice", state="West Bengal", season="kharif",
        acreage=3.0, gross_revenue=78588, total_cost=45000,
        net_margin=33588, risk_flag=False, price_source="cache",
        soil_code="alluvial", climate_zone="Tropical Wet",
    )
    with open(temp_log_file) as f:
        line = f.readline().strip()
    event = json.loads(line)
    assert event["crop"] == "rice"
    assert event["state"] == "West Bengal"
    assert event["net_margin"] == 33588


def test_log_contains_required_fields(temp_log_file):
    log_recommendation_event(
        crop="cotton", state="Maharashtra", season="kharif",
        acreage=4.0, gross_revenue=211840, total_cost=177600,
        net_margin=34240, risk_flag=False, price_source="default",
    )
    with open(temp_log_file) as f:
        event = json.loads(f.readline())
    for field in ("ts", "crop", "state", "season", "acreage",
                  "gross_revenue", "total_cost", "net_margin",
                  "risk_flag", "price_source"):
        assert field in event, f"Missing field: {field}"


def test_log_risk_flag_stored(temp_log_file):
    log_recommendation_event(
        crop="onion", state="Maharashtra", season="rabi",
        acreage=1.0, gross_revenue=25000, total_cost=23000,
        net_margin=2000, risk_flag=True, price_source="default",
    )
    with open(temp_log_file) as f:
        event = json.loads(f.readline())
    assert event["risk_flag"] is True


def test_log_multiple_events(temp_log_file):
    for i in range(5):
        log_recommendation_event(
            crop="wheat", state="Punjab", season="rabi",
            acreage=float(i + 1), gross_revenue=50000 * (i+1),
            total_cost=25000 * (i+1), net_margin=25000 * (i+1),
            risk_flag=False, price_source="default",
        )
    events = load_log_events()
    assert len(events) == 5


def test_load_events_empty_on_missing_file(temp_log_file):
    # Don't write anything
    events = load_log_events()
    assert events == []


def test_load_events_returns_list(temp_log_file):
    log_recommendation_event(
        crop="rice", state="Bihar", season="kharif",
        acreage=2.0, gross_revenue=52392, total_cost=38000,
        net_margin=14392, risk_flag=False, price_source="default",
    )
    events = load_log_events()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_get_log_summary_empty(temp_log_file):
    summary = get_log_summary()
    assert summary["total"] == 0
    assert summary["risk_count"] == 0


def test_get_log_summary_counts(temp_log_file):
    log_recommendation_event(
        crop="wheat", state="Punjab", season="rabi",
        acreage=2.0, gross_revenue=50000, total_cost=25000,
        net_margin=25000, risk_flag=False, price_source="default",
    )
    log_recommendation_event(
        crop="rice", state="Bihar", season="kharif",
        acreage=1.0, gross_revenue=8732, total_cost=16000,
        net_margin=-7268, risk_flag=True, price_source="cache",
    )
    summary = get_log_summary()
    assert summary["total"] == 2
    assert summary["risk_count"] == 1
    assert summary["risk_pct"] == 50.0


def test_log_never_raises_on_bad_input(temp_log_file):
    """Logger must never propagate exceptions to caller."""
    try:
        log_recommendation_event(
            crop="", state="", season="",
            acreage=0, gross_revenue=0, total_cost=0,
            net_margin=0, risk_flag=False, price_source="",
        )
    except Exception as e:
        pytest.fail(f"Logger raised exception on bad input: {e}")


def test_margin_per_acre_computed(temp_log_file):
    log_recommendation_event(
        crop="wheat", state="Punjab", season="rabi",
        acreage=4.0, gross_revenue=163800, total_cost=114800,
        net_margin=49000, risk_flag=False, price_source="default",
    )
    with open(temp_log_file) as f:
        event = json.loads(f.readline())
    assert event["margin_per_acre"] == round(49000 / 4.0)
