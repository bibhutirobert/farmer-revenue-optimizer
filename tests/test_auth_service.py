"""
Tests for auth_service — focus on fail-closed behaviour without secrets.
No real Google OAuth call is made (no [auth] in the test environment).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.auth_service import (
    is_auth_configured,
    is_logged_in,
    current_user_email,
    current_user_name,
    is_admin,
    get_oauth_profile_dict,
    sync_profile_once,
    require_login,
    require_admin,
)


def test_auth_not_configured_without_secrets():
    assert is_auth_configured() is False


def test_not_logged_in_without_secrets():
    assert is_logged_in() is False


def test_current_user_email_none_when_logged_out():
    assert current_user_email() is None


def test_current_user_name_none_when_logged_out():
    assert current_user_name() is None


def test_is_admin_false_when_logged_out():
    assert is_admin() is False


def test_get_oauth_profile_none_when_logged_out():
    assert get_oauth_profile_dict() is None


def test_sync_profile_once_noop_when_logged_out():
    # Must not raise and must not require a database connection.
    sync_profile_once("en")


def test_helpers_never_raise():
    try:
        is_auth_configured()
        is_logged_in()
        current_user_email()
        current_user_name()
        is_admin()
        get_oauth_profile_dict()
        sync_profile_once("en")
    except Exception as e:
        pytest.fail(f"auth_service helper raised an exception: {e}")


def test_require_login_never_raises_and_fails_closed():
    """
    Without secrets, require_login() must degrade gracefully (Streamlit's
    st.stop() is a no-op outside a real script run) rather than throwing,
    and must never leave is_logged_in() True as a side effect.
    """
    try:
        require_login("en")
    except Exception as e:
        pytest.fail(f"require_login raised an exception: {e}")
    assert is_logged_in() is False


def test_require_admin_never_raises_and_fails_closed():
    try:
        require_admin("en")
    except Exception as e:
        pytest.fail(f"require_admin raised an exception: {e}")
    assert is_admin() is False


# ── Secrets shape detection ───────────────────────────────────────────────────
# Streamlit's two [auth] layouts are not interchangeable: the nested form needs
# st.login("google"), the flat form needs st.login() with no argument. Getting
# this wrong looks like "correctly configured app stays permanently locked".

from core import auth_service


def _fake_secrets(monkeypatch, auth_block):
    class FakeSecrets:
        def get(self, key, default=None):
            return auth_block if key == "auth" else default

    monkeypatch.setattr(auth_service.st, "secrets", FakeSecrets())


BASE = {"redirect_uri": "https://x.example/oauth2callback", "cookie_secret": "s3cret"}
GOOGLE_KEYS = {
    "client_id": "abc.apps.googleusercontent.com",
    "client_secret": "shh",
    "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
}


def test_nested_google_section_is_detected(monkeypatch):
    _fake_secrets(monkeypatch, {**BASE, "google": GOOGLE_KEYS})
    assert auth_service.auth_provider() == "google"
    assert auth_service.is_auth_configured() is True


def test_flat_section_is_detected_as_default_provider(monkeypatch):
    _fake_secrets(monkeypatch, {**BASE, **GOOGLE_KEYS})
    assert auth_service.auth_provider() == "default"
    assert auth_service.is_auth_configured() is True


def test_missing_redirect_uri_is_not_configured(monkeypatch):
    _fake_secrets(monkeypatch, {"cookie_secret": "s3cret", "google": GOOGLE_KEYS})
    assert auth_service.auth_provider() is None


def test_missing_cookie_secret_is_not_configured(monkeypatch):
    _fake_secrets(monkeypatch, {"redirect_uri": "https://x/cb", "google": GOOGLE_KEYS})
    assert auth_service.auth_provider() is None


def test_base_keys_without_any_client_keys_is_not_configured(monkeypatch):
    _fake_secrets(monkeypatch, dict(BASE))
    assert auth_service.auth_provider() is None


def test_begin_login_passes_provider_name_for_nested(monkeypatch):
    _fake_secrets(monkeypatch, {**BASE, "google": GOOGLE_KEYS})
    calls = []
    monkeypatch.setattr(auth_service.st, "login", lambda *a: calls.append(a))
    auth_service.begin_login()
    assert calls == [("google",)]


def test_begin_login_passes_no_argument_for_flat(monkeypatch):
    _fake_secrets(monkeypatch, {**BASE, **GOOGLE_KEYS})
    calls = []
    monkeypatch.setattr(auth_service.st, "login", lambda *a: calls.append(a))
    auth_service.begin_login()
    assert calls == [()]


def test_begin_login_does_nothing_when_unconfigured(monkeypatch):
    _fake_secrets(monkeypatch, {})
    calls = []
    monkeypatch.setattr(auth_service.st, "login", lambda *a: calls.append(a))
    auth_service.begin_login()
    assert calls == []
