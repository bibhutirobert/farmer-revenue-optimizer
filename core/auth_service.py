"""
Auth Service — Google Sign-In (OpenID Connect)
=================================================
Uses Streamlit's native OIDC support (st.login / st.logout / st.user,
Authlib-backed) configured against Google as the identity provider. See
README "Authentication setup" for how to create the Google OAuth client
and fill in .streamlit/secrets.toml.

Sign-in is MANDATORY for the farmer advisory flow (require_login(), used by
pages/1, 2, 3, 5) — every farmer must have an account so their data forms a
complete, attributable picture (see get_oauth_profile_dict() /
sync_profile_once()). A second sign-in path, mobile number + OTP, is planned
for farmers without a Google account — see core/phone_auth_service.py
(currently a stub; the UI on page 1 already captures the number so
activating it later is a one-file change).

The internal Risk Intelligence dashboard has a stricter gate on top of
plain sign-in — only emails listed under [admin] emails in secrets can
open it (require_admin()). Admin status is never stored in the database,
only in that secrets allowlist, so it can't be escalated via a data row.

FALLBACK: if [auth] is not configured, every gate below fails CLOSED — the
advisory flow, "My Reports", and the dashboard all stay unavailable, with a
message explaining that the deployment isn't set up yet. Nothing ever runs
anonymously.
"""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st


def _auth_section() -> Mapping:
    try:
        return st.secrets.get("auth", {}) or {}
    except Exception:
        return {}


def auth_provider() -> Optional[str]:
    """
    Which provider name st.login() should be called with, or None if auth
    isn't usable yet.

    Streamlit accepts two shapes for [auth] and they are NOT interchangeable:

      nested  — [auth] holds redirect_uri/cookie_secret and a [auth.google]
                subsection holds the client keys. Used as st.login("google").
      flat    — the client keys sit directly under [auth]. Streamlit treats
                this as the "default" provider, and it only works when
                st.login() is called with no argument.

    Calling st.login("google") against a flat config raises StreamlitAuthError,
    and a nested config has no top-level client_id, so checking only for that
    reports "not configured" even when setup is perfect. Detecting the shape
    here means either layout works and neither fails silently.

    Nested is preferred — it is the documented multi-provider form, and it is
    what a second sign-in path (see core/phone_auth_service.py) would slot
    into as [auth.phone] without disturbing Google.
    """
    section = _auth_section()
    if not section:
        return None

    # Streamlit requires both of these regardless of shape; without them
    # st.login() raises rather than redirecting.
    if not section.get("redirect_uri") or not section.get("cookie_secret"):
        return None

    google = section.get("google")
    if isinstance(google, Mapping) and google.get("client_id") and google.get("client_secret"):
        return "google"

    if section.get("client_id") and section.get("client_secret"):
        return "default"

    return None


def is_auth_configured() -> bool:
    return auth_provider() is not None


def begin_login() -> None:
    """Start the OIDC redirect using whichever provider shape is configured."""
    provider = auth_provider()
    if provider == "default":
        st.login()
    elif provider:
        st.login(provider)


def is_logged_in() -> bool:
    if not is_auth_configured():
        return False
    try:
        user = getattr(st, "user", None)
        return bool(user) and bool(user.get("is_logged_in", False))
    except Exception:
        return False


def current_user_email() -> Optional[str]:
    if not is_logged_in():
        return None
    try:
        email = st.user.get("email")
        return email.strip().lower() if email else None
    except Exception:
        return None


def current_user_name() -> Optional[str]:
    if not is_logged_in():
        return None
    try:
        return st.user.get("name") or current_user_email()
    except Exception:
        return None


def _admin_emails() -> List[str]:
    try:
        raw = st.secrets.get("admin", {}).get("emails", [])
        return [e.strip().lower() for e in raw] if raw else []
    except Exception:
        return []


def is_admin() -> bool:
    email = current_user_email()
    return bool(email) and email in _admin_emails()


def get_oauth_profile_dict() -> Optional[Dict[str, Any]]:
    """
    Every claim Google's OIDC token gives us for the signed-in user, mapped
    to the profiles table (supabase/schema.sql). None if not logged in.
    This is deliberately "capture everything available" — email, name,
    given/family name, picture, locale, and the stable Google subject id —
    so the profile is as complete a picture as the identity provider allows.
    """
    if not is_logged_in():
        return None
    try:
        u = st.user
        email = (u.get("email") or "").strip().lower()
        if not email:
            return None
        return {
            "email": email,
            "google_sub": u.get("sub"),
            "full_name": u.get("name"),
            "given_name": u.get("given_name"),
            "family_name": u.get("family_name"),
            "picture_url": u.get("picture"),
            "locale": u.get("locale"),
        }
    except Exception:
        return None


def sync_profile_once(lang: str = "en") -> None:
    """
    Upsert the signed-in user's OAuth profile into Supabase, at most once
    per browser session (tracked in st.session_state) so repeated page
    loads don't hammer the database. Call from any gated page after
    require_login()/require_admin() succeeds. Silently does nothing if the
    database isn't configured or the write fails — profile sync must never
    block the advisory flow.
    """
    if not is_logged_in():
        return
    if st.session_state.get("_profile_synced"):
        return
    profile = get_oauth_profile_dict()
    if not profile:
        return
    try:
        from core.db_service import upsert_profile
        profile["preferred_lang"] = lang
        profile["last_login_at"] = datetime.now(timezone.utc).isoformat()
        upsert_profile(profile)
    except Exception:
        pass
    finally:
        st.session_state["_profile_synced"] = True


def render_account_widget(lang: str = "en") -> None:
    """Small sidebar sign-in/out control. Safe to call unconditionally —
    renders nothing if auth isn't configured."""
    if not is_auth_configured():
        return
    with st.sidebar:
        if is_logged_in():
            name = current_user_name()
            st.caption(("Signed in as" if lang == "en" else "साइन इन:") + f" {name}")
            if st.button("Sign out" if lang == "en" else "साइन आउट करें", key="_auth_logout"):
                st.logout()
        else:
            if st.button(
                "🔑 Sign in with Google" if lang == "en" else "🔑 Google से साइन इन करें",
                key="_auth_login",
            ):
                begin_login()


def require_login(lang: str = "en") -> None:
    """
    Gate a page to signed-in users only. Call at the very top of the page
    module, before any farm data is read or written. Halts execution
    (st.stop()) unless the caller is signed in. Never falls open — if
    [auth] isn't configured yet, the page stays unavailable rather than
    letting anonymous usage through.

    On success, also syncs the OAuth profile (sync_profile_once) so every
    account has a complete, up-to-date picture in the database.
    """
    if not is_auth_configured():
        st.error(
            "🔒 Sign-in isn't configured for this deployment yet. "
            "An account is required to use this app — please check back "
            "once the site owner finishes setup."
            if lang == "en"
            else "🔒 इस डिप्लॉयमेंट के लिए साइन-इन अभी कॉन्फ़िगर नहीं है। "
                 "इस ऐप का उपयोग करने के लिए खाता आवश्यक है — कृपया बाद में जांचें।"
        )
        st.stop()

    if not is_logged_in():
        st.warning(
            "🔑 Please sign in to continue. An account lets you save your "
            "farm reports and revisit them anytime."
            if lang == "en"
            else "🔑 जारी रखने के लिए कृपया साइन इन करें। खाता होने पर आप अपनी "
                 "खेत रिपोर्ट सहेज सकते हैं और कभी भी देख सकते हैं।"
        )
        if st.button("🔑 Sign in with Google" if lang == "en" else "🔑 Google से साइन इन करें",
                     key="_require_login_btn"):
            begin_login()
        st.stop()

    sync_profile_once(lang)


def require_admin(lang: str = "en") -> None:
    """Gate a page to admin-only. Call at the very top of the page module.
    Halts execution (st.stop()) unless the caller is signed in AND on the
    admin allowlist. Never falls open."""
    if not is_auth_configured():
        st.error(
            "🔒 Admin authentication is not configured for this deployment. "
            "This page is unavailable until [auth] is set up in secrets."
            if lang == "en"
            else "🔒 इस डिप्लॉयमेंट के लिए एडमिन प्रमाणीकरण कॉन्फ़िगर नहीं है।"
        )
        st.stop()

    if not is_logged_in():
        st.warning(
            "🔒 This is an internal, admin-only page. Please sign in."
            if lang == "en"
            else "🔒 यह एक आंतरिक, केवल-एडमिन पेज है। कृपया साइन इन करें।"
        )
        if st.button("Sign in with Google" if lang == "en" else "Google से साइन इन करें"):
            begin_login()
        st.stop()

    if not is_admin():
        st.error(
            f"🚫 Access denied for {current_user_email()} — not on the admin allowlist."
            if lang == "en"
            else f"🚫 पहुंच अस्वीकृत — {current_user_email()} एडमिन सूची में नहीं है।"
        )
        if st.button("Sign out" if lang == "en" else "साइन आउट करें"):
            st.logout()
        st.stop()

    sync_profile_once(lang)
