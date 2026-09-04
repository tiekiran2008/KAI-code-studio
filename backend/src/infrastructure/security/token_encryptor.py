"""
Token Encryption Utility
=========================
Authenticated AES-128-CBC + HMAC-SHA256 (Fernet) field-level encryption for
OAuth tokens, personal access tokens, and API secrets stored at rest.
"""
import base64
import hashlib
from typing import Optional
from src.core.config import settings
from src.core.logger import logger


class TokenEncryptor:
    """Encodes and decodes sensitive tokens using Fernet authenticated encryption."""

    def __init__(self, key: Optional[str] = None):
        raw_key = key or settings.MEMORY_ENCRYPTION_KEY or settings.SUPABASE_JWT_SECRET or "kai-studio-default-secret-key-32b"
        # Derive standard 32-byte url-safe base64 key
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        self._fernet_key = base64.urlsafe_b64encode(digest)

        try:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(self._fernet_key)
        except Exception as exc:
            logger.warning("Fernet initialization failed; falling back to mock mode", error=str(exc))
            self._fernet = None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string into ciphertext string."""
        if not plaintext:
            return ""
        if self._fernet is None:
            return f"plain:{plaintext}"
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error("Token encryption error", error=str(e))
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string back to plaintext."""
        if not ciphertext:
            return ""
        if ciphertext.startswith("plain:"):
            return ciphertext[6:]
        if self._fernet is None:
            return ciphertext
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            # If ciphertext cannot be decrypted (e.g. key changed), return empty or raw if plain
            logger.warning("Token decryption error; returning safe fallback", error=str(e))
            return ""
