"""
Phone OTP Service — STUB (not yet implemented)
=================================================
Placeholder for mobile-number sign-in / verification, planned as a second
sign-in path alongside Google (core/auth_service.py) for farmers who don't
have or don't want to use a Google account.

Candidate providers to wire in when ready:
  - MSP-friendly / India-first: MSG91, Kaleyra, Gupshup
  - General: Twilio Verify, Firebase Phone Auth

Until connected, is_otp_available() returns False and send_otp()/verify_otp()
are no-ops. Callers must treat every response as "not available yet" and
fall back to Google sign-in — never block the app on this.

What's already wired up so activation later is a one-file change:
  - profiles.phone_number / profiles.phone_verified columns exist
    (supabase/schema.sql) and core/db_service.save_phone_number() lets the
    UI capture an unverified number today.
  - pages/1_Land_Selection.py already has a "mobile number" input calling
    save_phone_number(); once verify_otp() is real, gate that save behind
    a successful verify_otp() call and flip phone_verified to True.
"""

from typing import Optional


def is_otp_available() -> bool:
    """Always False until a real SMS provider is connected below."""
    return False


def send_otp(phone_number: str) -> dict:
    """
    STUB — connect an SMS/OTP provider here.
    Expected real return: {"sent": True, "request_id": "..."}
    """
    return {"sent": False, "reason": "not_implemented"}


def verify_otp(phone_number: str, code: str, request_id: Optional[str] = None) -> bool:
    """STUB — always returns False until a real provider is connected."""
    return False
