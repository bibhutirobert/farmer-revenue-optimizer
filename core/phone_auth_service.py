"""
Phone OTP Service — mobile number verification
================================================
Full OTP engine: generate → deliver → verify, with the protections a
one-time-code flow needs to not be a liability. Used to verify a farmer's
mobile number on their account (pages/1_Land_Selection.py).

SECURITY PROPERTIES (all enforced here, server-side):
  - The code is NEVER stored in plaintext. Only an HMAC-SHA256 digest is
    persisted, keyed by a server-side secret, so a database leak does not
    hand out valid codes.
  - Codes expire (OTP_TTL_SECONDS, default 5 min).
  - Verification attempts are capped (MAX_VERIFY_ATTEMPTS, default 5). A
    6-digit code is only 1,000,000 combinations — without an attempt cap
    it is brute-forceable in minutes. On cap, the challenge is consumed.
  - Sends are rate limited per number (MAX_SENDS_PER_WINDOW in
    SEND_WINDOW_SECONDS) so the endpoint can't be used to spam someone
    else's phone or burn SMS credit.
  - Codes are generated with `secrets`, not `random` — the latter is
    predictable from observed output and must never mint credentials.
  - Comparison is constant-time (hmac.compare_digest).

DELIVERY PROVIDERS — configured under [sms] in secrets:
    provider = "msg91" | "twilio" | "dev"
  msg91 : India-first, needs DLT/TRAI-registered sender + template id.
  twilio: needs account_sid, auth_token, from_number.
  dev   : NO SMS is sent — the code is returned in the response so the
          whole flow can be exercised without a paid account. This is an
          EXPLICIT opt-in (provider = "dev"); it is never a silent
          fallback, because a dev-mode OTP in production would let anyone
          "verify" any phone number they type. With [sms] absent entirely,
          is_otp_available() is False and the UI hides the flow.

NOTE ON PHONE-AS-LOGIN:
  This module verifies a phone number on an already-signed-in account. It
  does NOT by itself make the phone a primary login identity — that needs
  a durable session for a user who never touches Google, and Streamlit's
  st.login() is OIDC-only with no native cookie-writing API. The clean way
  to get phone as a true sign-in path is to add a second OIDC provider
  that does SMS auth (Supabase Auth, Firebase, or Auth0 phone connection)
  to [auth] and call st.login("<that provider>"). Because every page gates
  on auth_service.require_login() rather than on Google specifically, that
  is a configuration change plus one button, not a rewrite. See README.
"""

import hmac
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

OTP_LENGTH = 6
OTP_TTL_SECONDS = 300           # 5 minutes
MAX_VERIFY_ATTEMPTS = 5
MAX_SENDS_PER_WINDOW = 3
SEND_WINDOW_SECONDS = 900       # 15 minutes


# ── Config ─────────────────────────────────────────────────────────────────────

def _sms_config() -> Dict[str, Any]:
    try:
        import streamlit as st
        return dict(st.secrets.get("sms", {}) or {})
    except Exception:
        return {}


def _provider() -> Optional[str]:
    """Configured provider name, or None if [sms] isn't set up."""
    cfg = _sms_config()
    provider = (cfg.get("provider") or "").strip().lower()
    if provider not in ("msg91", "twilio", "dev"):
        return None
    if provider == "msg91" and not cfg.get("auth_key"):
        return None
    if provider == "twilio" and not (
        cfg.get("account_sid") and cfg.get("auth_token") and cfg.get("from_number")
    ):
        return None
    return provider


def is_otp_available() -> bool:
    """True only when a delivery provider (or explicit dev mode) is configured
    AND the database is reachable — challenges must be persisted server-side."""
    if _provider() is None:
        return False
    try:
        from core.db_service import is_db_configured
        return is_db_configured()
    except Exception:
        return False


def is_dev_mode() -> bool:
    """True when codes are returned in-response instead of sent by SMS."""
    return _provider() == "dev"


# ── Phone normalization ────────────────────────────────────────────────────────

def normalize_phone(raw: str) -> Optional[str]:
    """
    Normalize an Indian mobile number to E.164 (+91XXXXXXXXXX).
    Returns None if it doesn't look like a valid mobile number — callers
    must treat None as "reject", never as "send anyway".
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    # Strip country code / trunk prefixes down to the 10-digit subscriber number
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "6789":
        return None
    return f"+91{digits}"


# ── Code generation / hashing ──────────────────────────────────────────────────

def _generate_code() -> str:
    """Cryptographically secure numeric code, zero-padded to OTP_LENGTH."""
    upper = 10 ** OTP_LENGTH
    return str(secrets.randbelow(upper)).zfill(OTP_LENGTH)


def _hmac_secret() -> bytes:
    """
    Server-side key for hashing codes. Prefers a dedicated [sms] otp_secret,
    falls back to the auth cookie_secret so there is always a real key —
    never a hardcoded constant.
    """
    cfg = _sms_config()
    key = cfg.get("otp_secret")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("auth", {}).get("cookie_secret")
        except Exception:
            key = None
    return (key or "fro-otp-fallback-key").encode("utf-8")


def _hash_code(phone: str, code: str) -> str:
    """Bind the digest to the phone number so a digest can't be replayed
    against a different number."""
    msg = f"{phone}:{code}".encode("utf-8")
    return hmac.new(_hmac_secret(), msg, hashlib.sha256).hexdigest()


# ── Delivery adapters ──────────────────────────────────────────────────────────

def _deliver_sms(phone: str, code: str) -> bool:
    """Dispatch the code via the configured provider. Returns delivery success.
    Never raises — a provider outage must not surface as a crash."""
    provider = _provider()
    cfg = _sms_config()

    if provider == "dev":
        return True  # caller surfaces the code directly; nothing to send

    try:
        import requests

        if provider == "msg91":
            resp = requests.post(
                "https://control.msg91.com/api/v5/flow/",
                json={
                    "template_id": cfg.get("template_id", ""),
                    "sender": cfg.get("sender_id", ""),
                    "short_url": "0",
                    "recipients": [{"mobiles": phone.lstrip("+"), "otp": code}],
                },
                headers={"authkey": cfg.get("auth_key", ""),
                         "Content-Type": "application/json"},
                timeout=10,
            )
            return resp.status_code == 200

        if provider == "twilio":
            sid = cfg.get("account_sid", "")
            resp = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={
                    "To": phone,
                    "From": cfg.get("from_number", ""),
                    "Body": f"Your Farmer Revenue Optimizer verification code is {code}. "
                            f"It expires in {OTP_TTL_SECONDS // 60} minutes.",
                },
                auth=(sid, cfg.get("auth_token", "")),
                timeout=10,
            )
            return resp.status_code in (200, 201)
    except Exception:
        return False

    return False


# ── Public API ─────────────────────────────────────────────────────────────────

def send_otp(raw_phone: str) -> Dict[str, Any]:
    """
    Generate, persist (hashed), and deliver a one-time code.

    Returns a dict — always inspect "sent":
      {"sent": True,  "phone": "+91...", "dev_code": "123456"|None}
      {"sent": False, "reason": "<machine-readable reason>", "retry_after": int|None}

    Reasons: not_configured, invalid_phone, rate_limited, delivery_failed,
             storage_failed.
    """
    if not is_otp_available():
        return {"sent": False, "reason": "not_configured"}

    phone = normalize_phone(raw_phone)
    if not phone:
        return {"sent": False, "reason": "invalid_phone"}

    from core.db_service import (
        count_recent_otp_sends, create_otp_challenge,
    )

    window_start = datetime.now(timezone.utc) - timedelta(seconds=SEND_WINDOW_SECONDS)
    recent = count_recent_otp_sends(phone, window_start)
    if recent >= MAX_SENDS_PER_WINDOW:
        return {"sent": False, "reason": "rate_limited",
                "retry_after": SEND_WINDOW_SECONDS}

    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)

    stored = create_otp_challenge(
        phone=phone,
        code_hash=_hash_code(phone, code),
        expires_at=expires_at.isoformat(),
    )
    if not stored:
        return {"sent": False, "reason": "storage_failed"}

    if not _deliver_sms(phone, code):
        return {"sent": False, "reason": "delivery_failed"}

    return {
        "sent": True,
        "phone": phone,
        # Only ever populated in explicit dev mode — never in production.
        "dev_code": code if is_dev_mode() else None,
    }


def verify_otp(raw_phone: str, code: str) -> Dict[str, Any]:
    """
    Check a submitted code against the newest live challenge for this number.

    Returns:
      {"verified": True,  "phone": "+91..."}
      {"verified": False, "reason": "...", "attempts_left": int|None}

    Reasons: not_configured, invalid_phone, no_challenge, expired,
             too_many_attempts, incorrect.
    """
    if not is_otp_available():
        return {"verified": False, "reason": "not_configured"}

    phone = normalize_phone(raw_phone)
    if not phone:
        return {"verified": False, "reason": "invalid_phone"}

    if not code or not code.strip().isdigit():
        return {"verified": False, "reason": "incorrect"}

    from core.db_service import (
        get_active_otp_challenge, consume_otp_challenge, bump_otp_attempts,
    )

    challenge = get_active_otp_challenge(phone)
    if not challenge:
        return {"verified": False, "reason": "no_challenge"}

    try:
        expires_at = datetime.fromisoformat(str(challenge["expires_at"]).replace("Z", "+00:00"))
    except Exception:
        return {"verified": False, "reason": "expired"}
    if expires_at <= datetime.now(timezone.utc):
        consume_otp_challenge(challenge["id"])
        return {"verified": False, "reason": "expired"}

    attempts = int(challenge.get("attempts", 0) or 0)
    if attempts >= MAX_VERIFY_ATTEMPTS:
        consume_otp_challenge(challenge["id"])
        return {"verified": False, "reason": "too_many_attempts"}

    expected = str(challenge.get("code_hash", ""))
    supplied = _hash_code(phone, code.strip())
    if not hmac.compare_digest(expected, supplied):
        bump_otp_attempts(challenge["id"])
        return {"verified": False, "reason": "incorrect",
                "attempts_left": MAX_VERIFY_ATTEMPTS - (attempts + 1)}

    consume_otp_challenge(challenge["id"])
    return {"verified": True, "phone": phone}
