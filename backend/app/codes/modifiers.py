from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.codes.em import is_em_code

__all__ = ["PROCEDURE_MODIFIERS", "VISIT_MODIFIERS", "allowed_modifiers", "modifier_meaning"]

VISIT_MODIFIERS: Mapping[str, str] = MappingProxyType(
    {
        "24": "Unrelated E/M during a postoperative period",
        "25": "Separately identifiable E/M on the same day",
        "57": "Decision for surgery",
        "93": "Audio-only telehealth",
        "95": "Audio-video telehealth",
        "AI": "Principal physician of record",
        "FS": "Split or shared visit",
    }
)

PROCEDURE_MODIFIERS: Mapping[str, str] = MappingProxyType(
    {
        "26": "Professional component",
        "50": "Bilateral procedure",
        "59": "Distinct procedural service",
        "76": "Repeat procedure by the same physician",
        "77": "Repeat procedure by another physician",
        "91": "Repeat clinical laboratory test",
        "LT": "Left side",
        "RT": "Right side",
        "XE": "Separate encounter",
        "XP": "Separate practitioner",
        "XS": "Separate structure",
        "XU": "Unusual non-overlapping service",
    }
)


def allowed_modifiers(code: str) -> Mapping[str, str]:
    return VISIT_MODIFIERS if is_em_code(code) else PROCEDURE_MODIFIERS


def modifier_meaning(code: str, modifier: str) -> str | None:
    return allowed_modifiers(code).get(modifier.strip().upper())
