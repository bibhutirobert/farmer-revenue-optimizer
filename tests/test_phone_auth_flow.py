"""
End-to-end tests for the OTP engine, with the provider and database faked
in-memory. These exercise the real send_otp/verify_otp code paths — expiry,
attempt caps, rate limiting, replay protection — without any network call
or Supabase project.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import core.phone_auth_service as pas
from core.phone_auth_service import (
    send_otp, verify_otp, MAX_VERIFY_ATTEMPTS, MAX_SENDS_PER_WINDOW,
)

PHONE = "+919876543210"


class FakeDB:
    """Minimal stand-in for the otp_challenges table."""

    def __init__(self):
        self.rows = []
        self._next_id = 1

    def create(self, phone, code_hash, expires_at):
        for r in self.rows:
            if r["phone"] == phone and not r["consumed"]:
                r["consumed"] = True
        self.rows.append({
            "id": self._next_id, "phone": phone, "code_hash": code_hash,
            "expires_at": expires_at, "attempts": 0, "consumed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self._next_id += 1
        return True

    def active(self, phone):
        live = [r for r in self.rows if r["phone"] == phone and not r["consumed"]]
        return sorted(live, key=lambda r: r["created_at"], reverse=True)[0] if live else None

    def bump(self, cid):
        for r in self.rows:
            if r["id"] == cid:
                r["attempts"] += 1
        return True

    def consume(self, cid):
        for r in self.rows:
            if r["id"] == cid:
                r["consumed"] = True
        return True

    def count_since(self, phone, since):
        since_s = since.isoformat() if hasattr(since, "isoformat") else since
        return len([r for r in self.rows
                    if r["phone"] == phone and r["created_at"] >= since_s])


@pytest.fixture
def otp_env(monkeypatch):
    """Wire the service to a fake DB and a dev-mode provider that 'delivers'
    without sending anything, so the returned dev_code drives the test."""
    db = FakeDB()

    monkeypatch.setattr(pas, "_provider", lambda: "dev")
    monkeypatch.setattr(pas, "is_otp_available", lambda: True)
    monkeypatch.setattr(pas, "is_dev_mode", lambda: True)
    monkeypatch.setattr(pas, "_hmac_secret", lambda: b"test-secret-key")

    fake_db_module = type("M", (), {
        "create_otp_challenge": staticmethod(
            lambda phone, code_hash, expires_at: db.create(phone, code_hash, expires_at)),
        "get_active_otp_challenge": staticmethod(lambda phone: db.active(phone)),
        "bump_otp_attempts": staticmethod(lambda cid: db.bump(cid)),
        "consume_otp_challenge": staticmethod(lambda cid: db.consume(cid)),
        "count_recent_otp_sends": staticmethod(
            lambda phone, since: db.count_since(phone, since)),
    })
    monkeypatch.setitem(sys.modules, "core.db_service", fake_db_module)
    return db


# ── Happy path ────────────────────────────────────────────────────────────────

def test_send_then_verify_succeeds(otp_env):
    sent = send_otp(PHONE)
    assert sent["sent"] is True
    result = verify_otp(PHONE, sent["dev_code"])
    assert result["verified"] is True
    assert result["phone"] == PHONE


def test_code_is_not_stored_in_plaintext(otp_env):
    sent = send_otp(PHONE)
    stored = otp_env.rows[-1]["code_hash"]
    assert sent["dev_code"] not in stored


def test_send_normalizes_number(otp_env):
    sent = send_otp("9876543210")
    assert sent["phone"] == PHONE


# ── Wrong codes / attempt cap ─────────────────────────────────────────────────

def test_wrong_code_is_rejected(otp_env):
    send_otp(PHONE)
    result = verify_otp(PHONE, "000000")
    assert result["verified"] is False
    assert result["reason"] == "incorrect"


def test_wrong_code_decrements_attempts_left(otp_env):
    send_otp(PHONE)
    first = verify_otp(PHONE, "000000")
    second = verify_otp(PHONE, "000000")
    assert first["attempts_left"] > second["attempts_left"]


def test_attempts_are_capped(otp_env):
    sent = send_otp(PHONE)
    for _ in range(MAX_VERIFY_ATTEMPTS):
        verify_otp(PHONE, "000000")
    # Even the CORRECT code must now fail — challenge is burned.
    result = verify_otp(PHONE, sent["dev_code"])
    assert result["verified"] is False


# ── Replay protection ─────────────────────────────────────────────────────────

def test_code_cannot_be_reused(otp_env):
    sent = send_otp(PHONE)
    assert verify_otp(PHONE, sent["dev_code"])["verified"] is True
    replay = verify_otp(PHONE, sent["dev_code"])
    assert replay["verified"] is False
    assert replay["reason"] == "no_challenge"


def test_resending_invalidates_the_previous_code(otp_env):
    first = send_otp(PHONE)
    second = send_otp(PHONE)
    assert verify_otp(PHONE, first["dev_code"])["verified"] is False
    assert verify_otp(PHONE, second["dev_code"])["verified"] is True


# ── Expiry ────────────────────────────────────────────────────────────────────

def test_expired_code_is_rejected(otp_env):
    sent = send_otp(PHONE)
    otp_env.rows[-1]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    result = verify_otp(PHONE, sent["dev_code"])
    assert result["verified"] is False
    assert result["reason"] == "expired"


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_sends_are_rate_limited(otp_env):
    for _ in range(MAX_SENDS_PER_WINDOW):
        assert send_otp(PHONE)["sent"] is True
    blocked = send_otp(PHONE)
    assert blocked["sent"] is False
    assert blocked["reason"] == "rate_limited"


def test_rate_limit_is_per_number(otp_env):
    for _ in range(MAX_SENDS_PER_WINDOW):
        send_otp(PHONE)
    other = send_otp("+919000000001")
    assert other["sent"] is True


# ── Cross-number isolation ────────────────────────────────────────────────────

def test_code_for_one_number_does_not_verify_another(otp_env):
    sent = send_otp(PHONE)
    other = "+919000000002"
    send_otp(other)
    result = verify_otp(other, sent["dev_code"])
    assert result["verified"] is False


def test_no_challenge_for_unknown_number(otp_env):
    result = verify_otp("+919000000003", "123456")
    assert result["verified"] is False
    assert result["reason"] == "no_challenge"


# ── Input validation ──────────────────────────────────────────────────────────

def test_invalid_phone_rejected_on_send(otp_env):
    assert send_otp("12345")["reason"] == "invalid_phone"


def test_non_numeric_code_rejected(otp_env):
    send_otp(PHONE)
    assert verify_otp(PHONE, "abcdef")["verified"] is False
