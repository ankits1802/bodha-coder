from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from app.codes.billing_codes import MAX_POINTERS, Code
from app.codes.ncci import NcciTables

__all__ = ["POINTER_LETTERS", "add_on_primaries", "line_pointers", "resolved_pointers"]

POINTER_LETTERS = "ABCDEFGHIJKL"


def line_pointers(codes: Sequence[Code], primaries: Mapping[str, str]) -> dict[str, tuple[str, ...]]:
    first = tuple(code.code for code in codes if code.type == "ICD-10")[:MAX_POINTERS]
    chosen = {code.code: code.pointers for code in codes if code.type == "CPT" and code.pointers}
    return {
        code.code: chosen.get(code.code) or chosen.get(primaries.get(code.code, ""), first)
        for code in codes
        if code.type == "CPT"
    }


def add_on_primaries(tables: NcciTables, codes: Sequence[Code], service_date: date) -> dict[str, str]:
    lines = [code.code for code in codes if code.type == "CPT"]
    found: dict[str, str] = {}
    for code in lines:
        rule = tables.add_on_primaries(code, service_date)
        primary = next((other for other in lines if rule is not None and other in rule.primaries), None)
        if primary is not None:
            found[code] = primary
    return found


def resolved_pointers(tables: NcciTables, codes: Sequence[Code], service_date: date) -> dict[str, tuple[str, ...]]:
    return line_pointers(codes, add_on_primaries(tables, codes, service_date))
