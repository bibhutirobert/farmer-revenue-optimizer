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
