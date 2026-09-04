"""
Unit Tests: TokenEncryptor
===========================
Tests encryption/decryption round-trips, fallback handling,
and edge cases for the Fernet-based field-level encryptor.
"""
import pytest


class TestTokenEncryptorRoundTrip:
    """Verify encrypt → decrypt recovers the original plaintext."""

    def _make_encryptor(self, key: str = "test-key-for-unit-tests-32bytes!"):
        from src.infrastructure.security.token_encryptor import TokenEncryptor
        return TokenEncryptor(key=key)

    def test_basic_roundtrip(self):
        enc = self._make_encryptor()
        token = "ghp_supersecrettoken1234567890"
        ciphertext = enc.encrypt(token)
        assert ciphertext != token, "Ciphertext must differ from plaintext"
        assert enc.decrypt(ciphertext) == token

    def test_encrypt_produces_different_ciphertexts(self):
        """Fernet uses random IV so two encryptions of the same plaintext must differ."""
        enc = self._make_encryptor()
        token = "ghp_repeatabletoken"
        c1 = enc.encrypt(token)
        c2 = enc.encrypt(token)
        assert c1 != c2, "Each encryption must produce a unique ciphertext"

    def test_empty_string_returns_empty(self):
        enc = self._make_encryptor()
        assert enc.encrypt("") == ""
        assert enc.decrypt("") == ""

    def test_wrong_key_returns_empty_on_decrypt(self):
        enc_a = self._make_encryptor("key-alpha-32bytesxxxxxxxxxxxxxxxx")
        enc_b = self._make_encryptor("key-beta-32bytesxxxxxxxxxxxxxxxxx")
        ciphertext = enc_a.encrypt("secret-value")
        result = enc_b.decrypt(ciphertext)
        # Must not raise; returns safe empty fallback
        assert result == ""

    def test_plain_prefix_passthrough(self):
        """plain: prefix legacy path should be transparent."""
        enc = self._make_encryptor()
        plain_ciphertext = "plain:ghp_legacytoken"
        assert enc.decrypt(plain_ciphertext) == "ghp_legacytoken"

    def test_long_token(self):
        enc = self._make_encryptor()
        token = "ghp_" + ("x" * 512)
        assert enc.decrypt(enc.encrypt(token)) == token

    def test_special_characters(self):
        enc = self._make_encryptor()
        token = "token with spaces & special chars: <>&=\"'"
        assert enc.decrypt(enc.encrypt(token)) == token


class TestTokenEncryptorKeyDerivation:
    """Verify that different raw keys produce different encryptors."""

    def test_different_keys_produce_different_ciphertexts(self):
        from src.infrastructure.security.token_encryptor import TokenEncryptor
        enc_a = TokenEncryptor(key="key-one-unique-32bytes-padded!!!")
        enc_b = TokenEncryptor(key="key-two-unique-32bytes-padded!!!")
        plaintext = "same-plaintext"
        c_a = enc_a.encrypt(plaintext)
        c_b = enc_b.encrypt(plaintext)
        # Ciphertexts may theoretically overlap in first few bytes but must be different overall
        assert c_a != c_b
