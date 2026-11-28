from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.errors import Unavailable

__all__ = ["SecretBox"]


@dataclass(frozen=True)
class SecretBox:
    prefix: str
    keys: str | None
    refusal: type[Unavailable]
    missing: str
    unreadable: str

    def is_sealed(self, stored: str) -> bool:
        return stored.startswith(self.prefix)

    def seal(self, secret: str) -> str:
        return self.prefix + MultiFernet(self._fernets()).encrypt(secret.encode()).decode()

    def open(self, stored: str) -> str:
        if not self.is_sealed(stored):
            raise self.refusal(self.unreadable)
        try:
            return MultiFernet(self._fernets()).decrypt(stored.removeprefix(self.prefix).encode()).decode()
        except InvalidToken as error:
            raise self.refusal(self.unreadable) from error

    def is_current(self, stored: str) -> bool:
        if not self.is_sealed(stored):
            return False
        try:
            self._fernets()[0].decrypt(stored.removeprefix(self.prefix).encode())
        except InvalidToken:
            return False
        return True

    def _fernets(self) -> list[Fernet]:
        listed = [key.strip() for key in (self.keys or "").split(",") if key.strip()]
        if not listed:
            raise self.refusal(self.missing)
        try:
            return [Fernet(key) for key in listed]
        except ValueError as error:
            raise self.refusal(self.missing) from error
