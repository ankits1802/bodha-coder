from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, get_args

from app.ai.contracts import Section

__all__ = ["PART_ORDER", "SECTION_ORDER", "TOP_UP_OPTIONAL", "Part", "in_part_order"]

Part = Literal["patient", "extracted_text", "em", "diagnoses", "code_review", "cdi", "audit", "mips"]

PART_ORDER: tuple[Part, ...] = get_args(Part)
SECTION_ORDER: tuple[Section, ...] = get_args(Section)
TOP_UP_OPTIONAL: frozenset[Part] = frozenset({"patient"})


def in_part_order(parts: Iterable[Part]) -> tuple[Part, ...]:
    chosen = set(parts)
    return tuple(part for part in PART_ORDER if part in chosen)
