"""Provider tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC). Key comes from SANTOSH_SECRET_KEY."""
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


class TokenVault:
    def __init__(self, key: str | None = None):
        key = key if key is not None else get_settings().secret_key
        if not key:
            # Dev only: an ephemeral key. Tokens will not survive a restart.
            key = Fernet.generate_key().decode()
            self.ephemeral = True
        else:
            self.ephemeral = False
        self._f = Fernet(key.encode() if isinstance(key, str) else key)

    def seal(self, token: str) -> str:
        return self._f.encrypt(token.encode()).decode()

    def open(self, sealed: str) -> str:
        try:
            return self._f.decrypt(sealed.encode()).decode()
        except InvalidToken as e:  # pragma: no cover - key rotated or wrong key
            raise ValueError("Token cannot be decrypted with the current key") from e


_vault: TokenVault | None = None


def vault() -> TokenVault:
    global _vault
    if _vault is None:
        _vault = TokenVault()
    return _vault
