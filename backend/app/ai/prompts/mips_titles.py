from __future__ import annotations

import re

from app.codes.mips_catalog import VERIFIED_MIPS_MEASURES, addable_measure

__all__ = ["measure_heading", "measure_title", "with_measure_headings"]

_HEADING_TOKEN = re.compile(r"\{\{measure (\d{3})\}\}")


def measure_title(measure_id: str) -> str:
    if measure_id in VERIFIED_MIPS_MEASURES:
        return VERIFIED_MIPS_MEASURES[measure_id][0]
    entry = addable_measure(measure_id)
    if entry is None:
        raise ValueError(f"MIPS #{measure_id} is not in the 2026 CMS measure catalog, so the prompt cannot name it.")
    return entry["title"]


def measure_heading(measure_id: str) -> str:
    return f"MIPS #{measure_id} - {measure_title(measure_id)}"


def with_measure_headings(text: str) -> str:
    return _HEADING_TOKEN.sub(lambda match: measure_heading(match.group(1)), text)
