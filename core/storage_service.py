"""
Storage Service — Supabase Storage Integration
=================================================
Stores generated PDF advisory reports for signed-in farmers so they can
revisit past reports ("My Reports") without recomputing them.

SECURITY MODEL:
  - Bucket `farm-reports` must be PRIVATE (created with public=False — see
    supabase/schema.sql). Files are never served by public URL.
  - Every object path is namespaced by a one-way hash of the owner's email
    (see _owner_prefix), never the raw email, so listing the bucket does not
    expose who owns what.
  - Reads happen only via short-lived signed URLs minted server-side with
    the service role key; a link is only ever handed to the owner who is
    already authenticated in this session.
  - Uses the same service-role client as db_service — see that module's
    docstring for the full key-handling rationale.

FALLBACK: if [supabase] is not configured, upload/sign functions return
None and callers simply skip the "save my report" feature.
"""

import hashlib
from typing import Optional

from core.db_service import get_client, is_db_configured  # reuse the same client

BUCKET = "farm-reports"
SIGNED_URL_TTL_SECONDS = 3600  # 1 hour


def is_storage_configured() -> bool:
    return is_db_configured()


def _owner_prefix(owner_email: str) -> str:
    """One-way, non-reversible folder name for an owner — never the raw email."""
    digest = hashlib.sha256(owner_email.strip().lower().encode("utf-8")).hexdigest()
    return digest[:24]


def upload_report_pdf(owner_email: str, filename: str, pdf_bytes: bytes) -> Optional[str]:
    """
    Upload a PDF to the farmer's private folder in the reports bucket.
    Returns the storage path on success, or None on failure/unconfigured.
    """
    client = get_client()
    if not client or not owner_email or not pdf_bytes:
        return None
    try:
        safe_name = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".")) or "report.pdf"
        path = f"{_owner_prefix(owner_email)}/{safe_name}"
        client.storage.from_(BUCKET).upload(
            path,
            pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        return path
    except Exception:
        return None


def get_signed_url(path: str, expires_in: int = SIGNED_URL_TTL_SECONDS) -> Optional[str]:
    """Mint a short-lived signed URL for a stored report. None on failure."""
    client = get_client()
    if not client or not path:
        return None
    try:
        resp = client.storage.from_(BUCKET).create_signed_url(path, expires_in)
        return resp.get("signedURL") or resp.get("signed_url")
    except Exception:
        return None
