import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _get_fernet_key() -> bytes:
    """
    Derive a 32-byte URL-safe base64-encoded key from ENCRYPTION_KEY or SECRET_KEY.
    This guarantees a valid Fernet key regardless of input key format.
    """
    raw_key = (settings.ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    digest = hashlib.sha256(raw_key).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plain_text: str) -> str:
    """
    Encrypts a secret string at rest.
    Returns URL-safe base64-encoded ciphertext string.
    """
    if not plain_text:
        return ""
    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(plain_text.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_secret(cipher_text: str) -> str:
    """
    Decrypts a previously encrypted secret string.
    Raises ValueError if ciphertext is invalid or tampered with.
    """
    if not cipher_text:
        return ""
    try:
        fernet = Fernet(_get_fernet_key())
        decrypted = fernet.decrypt(cipher_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid or corrupted ciphertext") from exc
