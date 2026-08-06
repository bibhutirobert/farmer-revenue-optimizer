"""
Tests for storage_service — fallback behaviour without Supabase secrets,
and the owner-folder hashing that keeps raw emails out of storage paths.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.storage_service import (
    is_storage_configured,
    upload_report_pdf,
    get_signed_url,
    _owner_prefix,
)


def test_storage_not_configured_without_secrets():
    assert is_storage_configured() is False


def test_upload_returns_none_without_db():
    assert upload_report_pdf("farmer@example.com", "report.pdf", b"%PDF-1.4") is None


def test_get_signed_url_returns_none_without_db():
    assert get_signed_url("some/path.pdf") is None


def test_owner_prefix_does_not_contain_raw_email():
    prefix = _owner_prefix("farmer@example.com")
    assert "farmer" not in prefix
    assert "@" not in prefix
    assert "example" not in prefix


def test_owner_prefix_is_deterministic():
    assert _owner_prefix("farmer@example.com") == _owner_prefix("Farmer@Example.com")


def test_owner_prefix_differs_per_owner():
    assert _owner_prefix("a@example.com") != _owner_prefix("b@example.com")


def test_functions_never_raise():
    try:
        is_storage_configured()
        upload_report_pdf("x@example.com", "r.pdf", b"data")
        get_signed_url("path.pdf")
    except Exception as e:
        pytest.fail(f"storage_service raised an exception: {e}")
