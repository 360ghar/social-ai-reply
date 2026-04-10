"""Unit tests for Fernet encryption module."""
import pytest

from app.utils.encryption import decrypt_text, encrypt_text


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch):
    """Ensure ENCRYPTION_KEY is set for all tests via Settings."""
    from app.core.config import Settings
    test_settings = Settings(encryption_key="test-encryption-key-for-unit-tests-min-32-ch")
    monkeypatch.setattr("app.utils.encryption.get_settings", lambda: test_settings)


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "my-secret-value"
        encrypted = encrypt_text(original)
        assert encrypted != original
        decrypted = decrypt_text(encrypted)
        assert decrypted == original

    def test_different_encryptions_for_same_text(self):
        e1 = encrypt_text("same-text")
        e2 = encrypt_text("same-text")
        assert e1 != e2

    def test_encrypt_empty_string(self):
        encrypted = encrypt_text("")
        assert decrypt_text(encrypted) == ""

    def test_encrypt_unicode(self):
        original = "こんにちは世界 🔐"
        encrypted = encrypt_text(original)
        assert decrypt_text(encrypted) == original
