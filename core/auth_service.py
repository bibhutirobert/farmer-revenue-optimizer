"""
Auth Service — Google Sign-In (OpenID Connect)
=================================================
Uses Streamlit's native OIDC support (st.login / st.logout / st.user,
Authlib-backed) configured against Google as the identity provider. See
README "Authentication setup" for how to create the Google OAuth client
and fill in .streamlit/secrets.toml.

Two things this unlocks:
  1. Optional sign-in for farmers, so their farm runs can be saved to
     "My Reports" (core/db_service.py) instead of vanishing at tab close.
  2. A hard gate on the internal Risk Intelligence dashboard — only
     emails listed under [admin] emails in secrets can open it.

FALLBACK: if [auth] is not configured, is_auth_configured() is False and
the app runs in guest mode — the full advisory flow works for everyone,
nothing is saved to an account, and admin-only pages stay locked to
everyone (never fail open).
"""

from typing import List, Optional

import streamlit as st


def is_auth_configured() -> bool:
    try:
        cfg = st.secrets.get("auth", {})
        return bool(cfg.get("client_id")) and bool(cfg.get("client_secret"))
    except Exception:
        return False


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
                st.login("google")


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
            st.login("google")
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
