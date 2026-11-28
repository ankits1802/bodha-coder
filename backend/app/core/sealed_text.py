from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.errors import Unavailable

__all__ = ["SEALED_PREFIX", "TextSeal", "is_sealed"]

SEALED_PREFIX = "v1:"


def is_sealed(stored: str) -> bool:
    return stored.startswith(SEALED_PREFIX)


@dataclass(frozen=True)
class TextSeal:
    keys_text: str | None
    not_set_up: str
    unreadable: str
    error: type[Unavailable] = Unavailable

    @property
    def ready(self) -> bool:
        try:
            self._keys()
        except Unavailable:
            return False
        return True

    def seal(self, value: str) -> str:
        return SEALED_PREFIX + MultiFernet(self._keys()).encrypt(value.encode()).decode()

    def open(self, stored: str) -> str:
        if not is_sealed(stored):
            raise self.error(self.unreadable)
        try:
            return MultiFernet(self._keys()).decrypt(stored.removeprefix(SEALED_PREFIX).encode()).decode()
        except InvalidToken as error:
            raise self.error(self.unreadable) from error

    def is_current(self, stored: str) -> bool:
        if not is_sealed(stored):
            return False
        try:
            self._keys()[0].decrypt(stored.removeprefix(SEALED_PREFIX).encode())
        except InvalidToken:
            return False
        return True

    def _keys(self) -> list[Fernet]:
        keys = [key.strip() for key in (self.keys_text or "").split(",") if key.strip()]
        if not keys:
            raise self.error(self.not_set_up)
        try:
            return [Fernet(key) for key in keys]
        except ValueError as error:
            raise self.error(self.not_set_up) from error
