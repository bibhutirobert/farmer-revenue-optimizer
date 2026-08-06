"""
Database Service — Supabase (Postgres) Integration
=====================================================
Persistent store for:
  - usage_events   : one row per recommendation run (replaces/augments the
                      local usage_log.jsonl and Google Sheet logger)
  - farm_records    : a signed-in farmer's saved farm runs ("My Reports")

SECURITY MODEL (read this before changing anything):
  This app is server-rendered (Streamlit) — there is no client-side code
  that ever talks to Supabase directly. Only this module, running on the
  server, does. Because of that:

    - We connect with the Supabase SERVICE ROLE key, never the anon key.
      The service role key must live only in .streamlit/secrets.toml
      (untracked — see .gitignore) or the Streamlit Cloud secrets manager.
      It must NEVER be sent to the browser or committed to git.
    - Row Level Security (RLS) is enabled on every table with NO policies
      granted to the `anon`/`authenticated` roles (see supabase/schema.sql).
      That means even if the anon key or a Supabase URL leaked, nothing is
      readable — only the service role (used exclusively here) bypasses RLS.
    - All per-user authorization (a farmer only ever sees their own saved
      reports) is therefore enforced in THIS module, not by Postgres RLS —
      every farm_records query is filtered by owner_email server-side.

FALLBACK:
  If [supabase] is not configured in secrets, every function below returns
  None/[]/False and callers fall back to their existing behaviour (local
  file, synthetic dashboard data, etc). The app never crashes because the
  database is not connected.
"""

from typing import Any, Dict, List, Optional


def is_db_configured() -> bool:
    try:
        import streamlit as st
        cfg = st.secrets.get("supabase", {})
        return bool(cfg.get("url")) and bool(cfg.get("service_role_key"))
    except Exception:
        return False


def get_client():
    """Lazy-load and cache a Supabase client using the service role key.

    Shared by db_service and storage_service — both need the same
    server-role connection, never a client-side/anon one.
    """
    try:
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _client():
            cfg = st.secrets.get("supabase", {})
            url = cfg.get("url", "")
            key = cfg.get("service_role_key", "")
            if not url or not key:
                return None
            from supabase import create_client
            return create_client(url, key)

        return _client()
    except Exception:
        return None


# ── Usage events (dashboard / risk intelligence) ───────────────────────────────

def save_usage_event(event: Dict[str, Any]) -> bool:
    """Insert one usage/recommendation event. Never raises."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("usage_events").insert(event).execute()
        return True
    except Exception:
        return False


def get_usage_events(limit: int = 5000) -> Optional[List[Dict[str, Any]]]:
    """Fetch recent usage events, newest first. Returns None if DB unavailable."""
    client = get_client()
    if not client:
        return None
    try:
        resp = (
            client.table("usage_events")
            .select("*")
            .order("ts", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return None


# ── Farm records ("My Reports" — requires sign-in) ─────────────────────────────

def save_farm_record(owner_email: str, record: Dict[str, Any]) -> Optional[str]:
    """
    Save a farm run for a signed-in farmer. `owner_email` scopes the row —
    always taken from the authenticated session (st.user.email), never from
    user-editable input, so a farmer cannot write into someone else's history.
    Returns the new record id, or None on failure.
    """
    client = get_client()
    if not client or not owner_email:
        return None
    try:
        payload = dict(record)
        payload["owner_email"] = owner_email.strip().lower()
        resp = client.table("farm_records").insert(payload).execute()
        rows = resp.data or []
        return rows[0]["id"] if rows else None
    except Exception:
        return None


def get_farm_history(owner_email: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch a signed-in farmer's own saved farm records, newest first."""
    client = get_client()
    if not client or not owner_email:
        return []
    try:
        resp = (
            client.table("farm_records")
            .select("*")
            .eq("owner_email", owner_email.strip().lower())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def delete_farm_record(owner_email: str, record_id: str) -> bool:
    """Delete one of the signed-in farmer's own records (ownership enforced here)."""
    client = get_client()
    if not client or not owner_email or not record_id:
        return False
    try:
        client.table("farm_records").delete().eq("id", record_id).eq(
            "owner_email", owner_email.strip().lower()
        ).execute()
        return True
    except Exception:
        return False


# ── Profiles (the "complete picture" record per signed-in user) ────────────────
# Admin status is deliberately NOT part of this table — see supabase/schema.sql.
# It stays solely in the [admin] emails allowlist in secrets.

def upsert_profile(profile: Dict[str, Any]) -> bool:
    """
    Insert a new profile row on first sign-in, or refresh it (name, picture,
    locale, last_login_at) on every later sign-in. `profile["email"]` is
    required and must come from the authenticated OIDC session, never from
    user-editable input.
    """
    client = get_client()
    email = (profile.get("email") or "").strip().lower()
    if not client or not email:
        return False
    try:
        payload = dict(profile)
        payload["email"] = email
        client.table("profiles").upsert(payload, on_conflict="email").execute()
        return True
    except Exception:
        return False


def get_profile(email: str) -> Optional[Dict[str, Any]]:
    """Fetch one profile by email. None if not found or DB unavailable."""
    client = get_client()
    if not client or not email:
        return None
    try:
        resp = (
            client.table("profiles")
            .select("*")
            .eq("email", email.strip().lower())
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def save_phone_number(email: str, phone_number: str) -> bool:
    """
    Attach a mobile number to a profile, unverified. Verification will be
    wired in later via core/phone_auth_service.py (currently a stub) — this
    only captures the number so the plumbing is ready.
    """
    client = get_client()
    if not client or not email or not phone_number:
        return False
    try:
        client.table("profiles").update(
            {"phone_number": phone_number.strip(), "phone_verified": False}
        ).eq("email", email.strip().lower()).execute()
        return True
    except Exception:
        return False


def get_all_profiles(limit: int = 2000) -> List[Dict[str, Any]]:
    """Admin-only: list all signed-in users. Callers must gate this behind
    core.auth_service.require_admin() — this function itself performs no
    authorization check, same as every other server-role query in this module."""
    client = get_client()
    if not client:
        return []
    try:
        resp = (
            client.table("profiles")
            .select("*")
            .order("last_login_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []
