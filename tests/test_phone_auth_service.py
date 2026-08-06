"""
Tests for phone_auth_service — this is a deliberate stub (no real SMS
provider connected yet). Tests just pin the "not implemented" contract so
callers keep treating it as unavailable until it's wired up for real.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.phone_auth_service import is_otp_available, send_otp, verify_otp


def test_otp_not_available():
    assert is_otp_available() is False


def test_send_otp_reports_not_implemented():
    result = send_otp("+919999999999")
    assert result["sent"] is False
    assert result["reason"] == "not_implemented"


def test_verify_otp_always_false():
    assert verify_otp("+919999999999", "123456") is False


def test_functions_never_raise():
    try:
        is_otp_available()
        send_otp("+919999999999")
        verify_otp("+919999999999", "000000")
    except Exception as e:
        pytest.fail(f"phone_auth_service raised an exception: {e}")
