from collections.abc import Sequence

__all__ = ["POINTER_CHOICE", "POINTER_KEY", "pointer_key", "read_pointer_key"]

POINTER_KEY = "pointers:"
POINTER_CHOICE = "accept"


def pointer_key(code: str, pointers: Sequence[str]) -> str:
    return f"{POINTER_KEY}{code}:{','.join(pointers)}"


def read_pointer_key(key: str) -> tuple[str, tuple[str, ...]] | None:
    if not key.startswith(POINTER_KEY):
        return None
    code, _, linked = key.removeprefix(POINTER_KEY).partition(":")
    return code, tuple(item for item in linked.split(",") if item)
