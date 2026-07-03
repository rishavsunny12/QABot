
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet_key(key: str | None = None) -> bytes:
    raw = key or settings.credentials_encryption_key
    try:
        return raw.encode() if isinstance(raw, str) else raw
    except Exception:
        return Fernet.generate_key()


class CredentialEncryption:
    """Encrypt and decrypt project credentials at rest."""

    def __init__(self, key: str | None = None):
        try:
            self._fernet = Fernet(_get_fernet_key(key))
        except Exception:
            dev_key = Fernet.generate_key()
            self._fernet = Fernet(dev_key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt credential") from exc


credential_encryption = CredentialEncryption()
