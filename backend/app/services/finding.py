from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["CODE_CHANGE_ACTIONS", "SEVERE_AUDIT", "Finding"]

CODE_CHANGE_ACTIONS = ("lower", "raise", "replace", "add", "remove", "review")
SEVERE_AUDIT = ("Critical",)


@dataclass(frozen=True)
class Finding:
    kind: str
    key: str
    action: str
    title: str
    reasoning: str
    code_before: str | None = None
    code_after: str | None = None
    evidence: tuple[str, ...] = ()
    severity: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    default_choice: str = "accept"
