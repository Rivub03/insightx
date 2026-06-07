# app/modules/datasources/credential_encryptor.py
#
# PURPOSE:
#   Encrypts credential dicts before writing to the DB and decrypts them
#   when a live connection is needed. Nothing else in the system accesses
#   raw credentials — all reads/writes go through this module.
#
# ALGORITHM: AES-256-GCM (Authenticated Encryption)
#   GCM mode produces a 16-byte authentication tag alongside the ciphertext.
#   If the stored string is tampered with or the wrong key is used, the
#   AESGCM.decrypt() call raises InvalidTag — this is intentional.
#
# LIBRARY: `cryptography` (pip install cryptography)
#   Uses AESGCM from cryptography.hazmat.primitives.ciphers.aead.
#   This is strictly better than AES-CBC for this use case because it
#   detects tampering (CBC does not).
#
# STORAGE FORMAT: "iv_hex:tag_hex:ciphertext_hex"
#   Three components, colon-delimited, all hex-encoded.
#   Stored as a single TEXT column in the datasources table.
#
# GENERATE A KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"
#   Add to .env:  CREDENTIAL_ENCRYPTION_KEY=<64-char hex string>

import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

# AES-256-GCM constants
_IV_BYTES  = 12  # 96-bit nonce — NIST recommended length for GCM
_TAG_BYTES = 16  # 128-bit authentication tag — maximum GCM security


def _get_key() -> bytes:
    """
    Validates and returns the encryption key from settings.
    Called at runtime (not at import time) so startup can proceed even if
    the key is not yet set — the first actual encrypt/decrypt call will fail
    loudly with a clear message.

    Returns:
        32-byte (256-bit) key as bytes

    Raises:
        ValueError: If the key is missing or not exactly 64 hex characters
    """
    hex_key = settings.credential_encryption_key

    if not hex_key or len(hex_key) != 64:
        raise ValueError(
            "CREDENTIAL_ENCRYPTION_KEY must be a 64-character hex string. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    try:
        return bytes.fromhex(hex_key)
    except ValueError:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY contains invalid hex characters")


def encrypt(credentials: dict) -> str:
    """
    Encrypts a credentials dict to a single storable string.

    The dict is JSON-serialised first, allowing any credential shape
    (password auth, wallet path, kerberos principal, etc.) to be stored
    in one TEXT column without needing separate encrypted columns per auth type.

    A fresh random IV is generated for every call.
    NEVER reuse an IV with the same key in GCM mode — doing so catastrophically
    breaks security guarantees.

    Args:
        credentials: Plain dict e.g. {"username": "sa", "password": "secret"}

    Returns:
        Encrypted string: "iv_hex:tag_hex:ciphertext_hex"
    """
    key = _get_key()
    iv  = os.urandom(_IV_BYTES)      # Fresh random nonce — never reuse

    aesgcm    = AESGCM(key)
    plaintext = json.dumps(credentials).encode("utf-8")

    # AESGCM.encrypt() returns ciphertext + tag concatenated (tag is the last 16 bytes)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext, None)

    ciphertext = ciphertext_and_tag[:-_TAG_BYTES]
    tag        = ciphertext_and_tag[-_TAG_BYTES:]

    return ":".join([iv.hex(), tag.hex(), ciphertext.hex()])


def decrypt(encrypted_string: str) -> dict:
    """
    Decrypts a stored encrypted credentials string back to the original dict.

    Raises cryptography.exceptions.InvalidTag if the string has been tampered
    with or the wrong encryption key is configured. Do not catch this silently —
    let it propagate as a 500 so the operator knows something is wrong.

    Args:
        encrypted_string: "iv_hex:tag_hex:ciphertext_hex" from the database

    Returns:
        The original credentials dict

    Raises:
        ValueError:                            Malformed string format
        cryptography.exceptions.InvalidTag:    Tampered data or wrong key
    """
    parts = encrypted_string.split(":")

    if len(parts) != 3:
        raise ValueError(
            "Malformed encrypted credential — expected format 'iv_hex:tag_hex:ciphertext_hex'"
        )

    try:
        iv         = bytes.fromhex(parts[0])
        tag        = bytes.fromhex(parts[1])
        ciphertext = bytes.fromhex(parts[2])
    except ValueError as exc:
        raise ValueError(f"Encrypted credential contains invalid hex data: {exc}") from exc

    key    = _get_key()
    aesgcm = AESGCM(key)

    # Re-assemble: AESGCM.decrypt() expects ciphertext + tag concatenated
    plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)

    return json.loads(plaintext.decode("utf-8"))