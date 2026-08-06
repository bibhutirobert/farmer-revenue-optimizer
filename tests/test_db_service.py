"""
Tests for db_service — focus on graceful fallback when Supabase is not
configured (no [supabase] secrets in the test environment). No real
network call is made.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.db_service import (
    is_db_configured,
    get_client,
    save_usage_event,
    get_usage_events,
    save_farm_record,
    get_farm_history,
    delete_farm_record,
    upsert_profile,
    get_profile,
    save_phone_number,
    get_all_profiles,
)


def test_db_not_configured_without_secrets():
    assert is_db_configured() is False


def test_get_client_none_without_secrets():
    assert get_client() is None


def test_save_usage_event_returns_false_without_db():
    assert save_usage_event({"crop": "wheat"}) is False


def test_get_usage_events_returns_none_without_db():
    assert get_usage_events() is None


def test_save_farm_record_returns_none_without_db():
    assert save_farm_record("farmer@example.com", {"crop": "wheat", "acreage": 2}) is None


def test_get_farm_history_returns_empty_list_without_db():
    assert get_farm_history("farmer@example.com") == []


def test_delete_farm_record_returns_false_without_db():
    assert delete_farm_record("farmer@example.com", "some-id") is False


def test_save_farm_record_requires_owner_email():
    assert save_farm_record("", {"crop": "wheat"}) is None


def test_upsert_profile_returns_false_without_db():
    assert upsert_profile({"email": "farmer@example.com", "full_name": "Test Farmer"}) is False


def test_upsert_profile_requires_email():
    assert upsert_profile({"full_name": "No Email"}) is False


def test_get_profile_returns_none_without_db():
    assert get_profile("farmer@example.com") is None


def test_save_phone_number_returns_false_without_db():
    assert save_phone_number("farmer@example.com", "+919999999999") is False


def test_save_phone_number_requires_both_args():
    assert save_phone_number("", "+919999999999") is False
    assert save_phone_number("farmer@example.com", "") is False


def test_get_all_profiles_returns_empty_list_without_db():
    assert get_all_profiles() == []


def test_functions_never_raise():
    try:
        is_db_configured()
        get_client()
        save_usage_event({})
        get_usage_events()
        save_farm_record("x@example.com", {})
        get_farm_history("x@example.com")
        delete_farm_record("x@example.com", "id")
        upsert_profile({"email": "x@example.com"})
        get_profile("x@example.com")
        save_phone_number("x@example.com", "+911234567890")
        get_all_profiles()
    except Exception as e:
        pytest.fail(f"db_service raised an exception: {e}")
