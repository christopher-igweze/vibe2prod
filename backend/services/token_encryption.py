"""Symmetric encryption helpers for sensitive database fields.

GitHub OAuth access tokens are encrypted before being written to the database
and decrypted only in application memory when they are needed for API calls.
This means a raw database dump or SQL injection attack exposes only ciphertext,
not usable tokens.

Algorithm: AES-256-GCM (authenticated encryption with associated data, AEAD).
  - Provides both *confidentiality* (tokens can't be read) and *integrity*
    (tampering with ciphertext is detected and raises an error rather than
    silently returning garbage).

Key material: A 32-byte (256-bit) key supplied as a URL-safe base64-encoded
environment variable ``GITHUB_TOKEN_ENCRYPTION_KEY``.

Generate a new key with::

    python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

Wire format stored in the database (plain ASCII, safe for VARCHAR columns)::

    <base64(nonce)>.<base64(ciphertext+tag)>

The nonce is 12 bytes (96 bits), generated freshly for every encrypt call.
Each token therefore has an independent nonce, so encrypting the same token
twice produces different ciphertext — no information about value repetition
leaks to an observer of the database.
"""

from __future__ import annotations

import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# Separator character that cannot appear in URL-safe base64 output.
_SEP = "."

# Number of random bytes used as the GCM nonce (IV).
_NONCE_BYTES = 12


def _load_key(raw_key: str | None) -> bytes:
    """Decode and validate the base64-encoded encryption key.

    Args:
        raw_key: URL-safe base64-encoded 32-byte key, or None / empty string
                 when encryption is not configured.

    Returns:
        32-byte key material.

    Raises:
        ValueError: If the key is present but cannot be decoded or is not
                    exactly 32 bytes after decoding.
    """
    if not raw_key:
        raise ValueError(
            "GITHUB_TOKEN_ENCRYPTION_KEY is not set. "
            "Generate a key with: "
            "python -c \"import secrets, base64; "
            "print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
        )
    try:
        key_bytes = base64.urlsafe_b64decode(raw_key + "==")  # pad defensively
    except Exception as exc:
        raise ValueError(
            "GITHUB_TOKEN_ENCRYPTION_KEY is not valid base64."
        ) from exc
    if len(key_bytes) != 32:
        raise ValueError(
            f"GITHUB_TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes "
            f"(got {len(key_bytes)}). "
            "Generate a new key with: "
            "python -c \"import secrets, base64; "
            "print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
        )
    return key_bytes


def encrypt_token(plaintext: str, raw_key: str | None = None) -> str:
    """Encrypt *plaintext* (e.g. a GitHub OAuth token) for storage.

    Args:
        plaintext: The sensitive string to protect.
        raw_key: URL-safe base64-encoded 32-byte AES key.  When *None* the
                 value is read from the ``GITHUB_TOKEN_ENCRYPTION_KEY``
                 environment variable (useful for tests that set ``os.environ``
                 directly).

    Returns:
        An ASCII string of the form ``<nonce_b64>.<ciphertext_b64>`` that is
        safe to store in any text column.

    Raises:
        ValueError: If the key is missing or invalid.
    """
    if raw_key is None:
        raw_key = os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY")
    key_bytes = _load_key(raw_key)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    nonce_b64 = base64.urlsafe_b64encode(nonce).decode()
    ciphertext_b64 = base64.urlsafe_b64encode(ciphertext).decode()
    return f"{nonce_b64}{_SEP}{ciphertext_b64}"


def decrypt_token(ciphertext_field: str, raw_key: str | None = None) -> str:
    """Decrypt a value previously encrypted by :func:`encrypt_token`.

    Args:
        ciphertext_field: The stored string in the form
                          ``<nonce_b64>.<ciphertext_b64>``.
        raw_key: URL-safe base64-encoded 32-byte AES key.  When *None* the
                 value is read from the ``GITHUB_TOKEN_ENCRYPTION_KEY``
                 environment variable.

    Returns:
        The original plaintext string.

    Raises:
        ValueError: If the key is missing, invalid, or the stored value is not
                    in the expected wire format.
        cryptography.exceptions.InvalidTag: If the ciphertext has been tampered
                    with (authentication failure). Callers should treat this the
                    same as a missing token — the stored credential is unusable.
    """
    if raw_key is None:
        raw_key = os.environ.get("GITHUB_TOKEN_ENCRYPTION_KEY")
    key_bytes = _load_key(raw_key)

    parts = ciphertext_field.split(_SEP, 1)
    if len(parts) != 2:
        raise ValueError(
            "Stored token is not in the expected encrypted format "
            f"('<nonce_b64>{_SEP}<ciphertext_b64>'). "
            "The database may contain a plaintext token from before encryption "
            "was introduced. Revoke and re-issue the token."
        )
    nonce_b64, ct_b64 = parts
    try:
        nonce = base64.urlsafe_b64decode(nonce_b64 + "==")
        ciphertext = base64.urlsafe_b64decode(ct_b64 + "==")
    except Exception as exc:
        raise ValueError("Stored token contains invalid base64 data.") from exc

    aesgcm = AESGCM(key_bytes)
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext_bytes.decode()


def is_encrypted(value: str) -> bool:
    """Return *True* if *value* looks like output from :func:`encrypt_token`.

    This heuristic is useful for migration paths where the database may
    contain a mix of legacy plaintext tokens and freshly encrypted ones.
    The check is intentionally conservative: it only confirms the wire-format
    separator is present — it does *not* attempt decryption.

    Args:
        value: A string read from the database column.

    Returns:
        ``True`` when the value contains exactly one ``"."`` separator and
        both halves are non-empty, ``False`` otherwise.
    """
    parts = value.split(_SEP, 1)
    return (
        len(parts) == 2
        and bool(parts[0])
        and bool(parts[1])
    )
