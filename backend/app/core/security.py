# app/core/security.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# In a real production environment, this key MUST be loaded from an environment variable.
# Example: bytes.fromhex(os.getenv("INSIGHTX_AES_KEY"))
# For this scaffold, we generate a static key for testing consistency.
_STATIC_KEY = b'12345678901234567890123456789012' # 32 bytes = 256 bits

def encrypt_credential(plaintext: str) -> str:
    """Encrypts credentials using AES-256-GCM."""
    if not plaintext:
        return ""
    aesgcm = AESGCM(_STATIC_KEY)
    nonce = os.urandom(12) # GCM requires a unique 12-byte nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    # Store the nonce and ciphertext together as a single hex string
    return (nonce + ciphertext).hex()

def decrypt_credential(ciphertext_hex: str) -> str:
    """Decrypts database credentials for on-the-fly driver execution."""
    if not ciphertext_hex:
        return ""
    data = bytes.fromhex(ciphertext_hex)
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(_STATIC_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')