from __future__ import annotations

from typing import Any

__all__ = ["matched_choice"]


def matched_choice(value: Any, options: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        wanted = value.strip().lower()
        for option in options:
            if wanted == option.lower():
                return option
    return value
