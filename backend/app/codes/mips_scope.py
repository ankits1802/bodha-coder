from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.codes.mips_catalog import ADDABLE_MEASURE_IDS, VERIFIED_MIPS_MEASURES, list_order, rejection_for_saved_id

MipsScopeSource = Literal["practice"]

_ECHO_LIMIT = 40


@dataclass(frozen=True)
class MipsScope:
    measure_ids: tuple[str, ...]
    source: MipsScopeSource
    retired_ids: tuple[str, ...] = ()

    @property
    def added_ids(self) -> tuple[str, ...]:
        return tuple(measure_id for measure_id in self.measure_ids if measure_id in ADDABLE_MEASURE_IDS)


def _echo(value: object) -> str:
    text = repr(value)
    return text if len(text) <= _ECHO_LIMIT else text[: _ECHO_LIMIT - 1] + "…"


def validate_measure_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError('measureIds must be a list of MIPS measure ids, e.g. ["001", "226"].')
    chosen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"measureIds must contain only measure ids as text; got {_echo(item)}.")
        if item not in VERIFIED_MIPS_MEASURES and item not in ADDABLE_MEASURE_IDS:
            raise rejection_for_saved_id(item)
        chosen.add(item)
    return list_order(chosen)


def catalog_ids(stored: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(stored, list):
        return (), ()
    kept = tuple(list_order(stored))
    retired: list[str] = []
    for item in stored:
        if isinstance(item, str) and item in kept:
            continue
        text = item if isinstance(item, str) else repr(item)
        if text not in retired:
            retired.append(text)
    return kept, tuple(retired)


def practice_scope(stored: object) -> MipsScope | None:
    if not isinstance(stored, list) or not stored:
        return None
    kept, retired = catalog_ids(stored)
    return MipsScope(measure_ids=kept, source="practice", retired_ids=retired)
