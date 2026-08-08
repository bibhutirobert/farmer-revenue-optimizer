"""
Tests for phone_auth_service.

Two groups:
  1. Not-configured behaviour — with no [sms] secrets, the whole flow must
     stay unavailable and fail closed (no network calls, no crashes).
  2. Pure-logic units that don't need a provider or database: phone
     normalization, code generation, and the HMAC hashing that keeps
     plaintext codes out of the database.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.phone_auth_service import (
    is_otp_available,
    is_dev_mode,
    send_otp,
    verify_otp,
    normalize_phone,
    _generate_code,
    _hash_code,
    OTP_LENGTH,
    MAX_VERIFY_ATTEMPTS,
)


# ── Not configured → fails closed ─────────────────────────────────────────────

def test_otp_not_available_without_secrets():
    assert is_otp_available() is False


def test_dev_mode_off_without_secrets():
    assert is_dev_mode() is False


def test_send_otp_reports_not_configured():
    assert send_otp("+919876543210")["reason"] == "not_configured"


def test_verify_otp_reports_not_configured():
    result = verify_otp("+919876543210", "123456")
    assert result["verified"] is False
    assert result["reason"] == "not_configured"


def test_functions_never_raise():
    try:
        is_otp_available()
        is_dev_mode()
        send_otp("+919876543210")
        send_otp("garbage")
        verify_otp("+919876543210", "000000")
        verify_otp("", "")
    except Exception as e:
        pytest.fail(f"phone_auth_service raised an exception: {e}")


# ── Phone normalization ───────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    "9876543210",
    "+919876543210",
    "919876543210",
    "09876543210",
    "+91 98765 43210",
    "98765-43210",
])
def test_normalize_accepts_valid_indian_mobiles(raw):
    assert normalize_phone(raw) == "+919876543210"


@pytest.mark.parametrize("raw", [
    "",
    None,
    "12345",                # too short
    "5876543210",           # invalid leading digit for Indian mobile
    "98765432101234",       # too long
    "abcdefghij",
])
def test_normalize_rejects_invalid(raw):
    assert normalize_phone(raw) is None


def test_normalize_is_idempotent():
    once = normalize_phone("9876543210")
    assert normalize_phone(once) == once


# ── Code generation ───────────────────────────────────────────────────────────

def test_generated_code_has_expected_length():
    assert len(_generate_code()) == OTP_LENGTH


def test_generated_code_is_numeric():
    assert _generate_code().isdigit()


def test_generated_codes_vary():
    """Sanity check that codes aren't constant (secrets-backed, not fixed)."""
    codes = {_generate_code() for _ in range(50)}
    assert len(codes) > 1


# ── Hashing ───────────────────────────────────────────────────────────────────

def test_hash_is_not_the_plaintext_code():
    digest = _hash_code("+919876543210", "123456")
    assert "123456" not in digest


def test_hash_is_deterministic():
    a = _hash_code("+919876543210", "123456")
    b = _hash_code("+919876543210", "123456")
    assert a == b


def test_hash_differs_per_code():
    a = _hash_code("+919876543210", "123456")
    b = _hash_code("+919876543210", "654321")
    assert a != b


def test_hash_is_bound_to_phone_number():
    """Same code, different number must not produce the same digest —
    otherwise a digest could be replayed against another number."""
    a = _hash_code("+919876543210", "123456")
    b = _hash_code("+919999999999", "123456")
    assert a != b


# ── Policy constants ──────────────────────────────────────────────────────────

def test_attempt_cap_is_low_enough_to_stop_brute_force():
    """A 6-digit code is 1e6 combinations; the cap must be a small number."""
    assert 1 <= MAX_VERIFY_ATTEMPTS <= 10
