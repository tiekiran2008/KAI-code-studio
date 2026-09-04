"""
Memory Encryptor
================
Fernet-based (AES-128-CBC + HMAC-SHA256) field-level encryption for
sensitive memory content.

Design Decisions
----------------
* **Fernet** is chosen over raw AES because it provides authenticated
  encryption — any tampering of the ciphertext raises InvalidToken,
  preventing silent data corruption.
* The key is loaded from the environment (`MEMORY_ENCRYPTION_KEY`) as a
  URL-safe base64-encoded 32-byte value. If no key is configured the
  encryptor operates in PASSTHROUGH mode (no-op), which is acceptable for
  development environments.
* The encryptor is stateless and thread-safe; inject it as a singleton.
"""
from __future__ import annotations

import base64
import os

from src.domain.memory.ports import IMemoryEncryptor
from src.core.logger import logger


class FernetMemoryEncryptor(IMemoryEncryptor):
    """
    Concrete encryptor using the ``cryptography`` library's Fernet recipe.
    Falls back to a no-op passthrough when no key is configured so that
    tests and development environments work without cryptographic setup.
    """

    def __init__(self, key: str | None = None) -> None:
        raw_key = key or os.getenv("MEMORY_ENCRYPTION_KEY", "")
        if raw_key:
            try:
                from cryptography.fernet import Fernet  # type: ignore
                self._fernet = Fernet(raw_key.encode())
                self._enabled = True
                logger.info("memory_encryptor_init", mode="fernet")
            except Exception as exc:
                logger.warning(
                    "memory_encryptor_fernet_init_failed",
                    error=str(exc),
                    fallback="passthrough",
                )
                self._fernet = None
                self._enabled = False
        else:
            self._fernet = None
            self._enabled = False
            logger.info("memory_encryptor_init", mode="passthrough")

    # ------------------------------------------------------------------
    # IMemoryEncryptor implementation
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        if not self._enabled or self._fernet is None:
            return plaintext
        token: bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not self._enabled or self._fernet is None:
            return ciphertext
        try:
            from cryptography.fernet import InvalidToken  # type: ignore
            plaintext: bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Memory decryption failed: {exc}") from exc

    @property
    def is_enabled(self) -> bool:
        return self._enabled
