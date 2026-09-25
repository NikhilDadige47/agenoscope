import pytest
from app.core.encryption import encrypt_secret, decrypt_secret


def test_encryption_roundtrip():
    plain = "ls__test_api_key_1234567890abcdef"
    cipher = encrypt_secret(plain)
    assert cipher != plain
    assert len(cipher) > len(plain)
    
    decrypted = decrypt_secret(cipher)
    assert decrypted == plain


def test_encryption_empty_string():
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_encryption_unicode():
    plain = "ls__密钥_unicode_key!@#$%^&*()_+"
    cipher = encrypt_secret(plain)
    assert decrypt_secret(cipher) == plain


def test_decryption_invalid_ciphertext():
    with pytest.raises(ValueError, match="Invalid or corrupted ciphertext"):
        decrypt_secret("invalid-ciphertext-data")
