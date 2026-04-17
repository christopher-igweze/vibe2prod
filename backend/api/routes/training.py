"""Training data ingestion — anonymized forgeignore suppression patterns.

CLI users authenticate with ``X-API-Key: v2p_...`` header.  When present,
the training entry is linked to their account via SHA-256 hash lookup.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Request, HTTPException

from services import supabase_client as db

router = APIRouter()
logger = logging.getLogger(__name__)


async def _resolve_api_key(request: Request) -> str | None:
    """Resolve an X-API-Key header to a user_id, or None."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return None
    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return await db.lookup_user_by_api_key(key_hash)
    except Exception:
        logger.exception("Failed to resolve API key to user_id")
        return None


@router.post("/training/forgeignore")
async def ingest_forgeignore(request: Request):
    """Ingest anonymized .forgeignore entries for training data.

    Auth is optional — anonymous submissions allowed.
    With X-API-Key header, entries are linked to the user.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    user_id = await _resolve_api_key(request)

    repo_hash = body.get("repo_hash", "")
    entries = body.get("entries", [])
    scan_mode = body.get("scan_mode", "full")
    version = body.get("version", "")

    if not entries:
        return {"accepted": 0, "duplicates": 0}

    rows = []
    for entry in entries:
        pattern = entry.get("pattern", "") or entry.get("rule_family", "")
        category = entry.get("category", "") or entry.get("type", "")
        entry_type = entry.get("type", "false_positive")
        reason = entry.get("reason", "")

        if not pattern or not reason:
            continue

        fingerprint = hashlib.sha256(
            f"{pattern}:{category}:{entry_type}".encode()
        ).hexdigest()

        rows.append({
            "fingerprint": fingerprint,
            "user_id": user_id,
            "repo_hash": repo_hash,
            "pattern": pattern,
            "category": category,
            "reason": reason,
            "type": entry_type,
            "check_id": entry.get("check_id"),
            "path_glob": entry.get("path"),
            "max_severity": entry.get("max_severity"),
            "scan_mode": scan_mode,
            "version": version,
        })

    if not rows:
        return {"accepted": 0, "duplicates": 0}

    try:
        accepted = await db.store_forgeignore_entries_batch(rows)
    except Exception:
        logger.exception("Failed to batch insert forgeignore entries")
        accepted = 0

    return {"accepted": accepted, "duplicates": len(rows) - accepted}
