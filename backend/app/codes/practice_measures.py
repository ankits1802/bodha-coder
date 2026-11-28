from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from app.codes.billing_codes import CPT_PATTERN, MODIFIER_PATTERN
from app.codes.mips_catalog import CMS_MIPS_INDEX, VERIFIED_MIPS_MEASURES, normalise_measure_input

__all__ = [
    "CODES_PER_OUTCOME",
    "KEY_LIMIT",
    "PRACTICE_MEASURE_ID_PREFIX",
    "PracticeMeasureDefinition",
    "PracticeMeasureRejected",
    "checked_codes",
    "checked_identifier",
    "checked_name",
    "checked_text",
    "is_practice_key",
    "key_for",
    "key_number",
    "practice_key_in_answer",
    "required_text",
]

PRACTICE_MEASURE_ID_PREFIX = "PRACTICE #"
KEY_LIMIT = 999
CODES_PER_OUTCOME = 4

_KEY = re.compile(r"^P(\d{3})$")
_ANSWER_KEY = re.compile(r"^\s*(?:practice\s*)?(?:measure\s*)?#?\s*(P\d{3})\s*$", re.IGNORECASE)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./_-]*$")
_SPACES = re.compile(r"[ \t]+")
_ECHO_LIMIT = 12


@dataclass(frozen=True)
class PracticeMeasureDefinition:
    key: str
    version: int
    version_id: str
    name: str
    identifier: str | None
    in_scope: str
    out_of_scope: str | None
    to_meet: str
    met_codes: tuple[str, ...] = ()
    not_met_codes: tuple[str, ...] = ()

    @property
    def mips_id(self) -> str:
        return f"{PRACTICE_MEASURE_ID_PREFIX}{self.key}"


class PracticeMeasureRejected(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def key_for(number: int) -> str:
    if not 1 <= number <= KEY_LIMIT:
        raise PracticeMeasureRejected(f"a practice can define at most {KEY_LIMIT} measures over its lifetime")
    return f"P{number:03d}"


def key_number(key: str) -> int:
    match = _KEY.match(key)
    if match is None:
        raise ValueError(f"{key!r} is not a practice measure key")
    return int(match.group(1))


def is_practice_key(value: object) -> bool:
    return isinstance(value, str) and _KEY.match(value) is not None


def practice_key_in_answer(mips_id: object) -> str | None:
    if not isinstance(mips_id, str):
        return None
    match = _ANSWER_KEY.match(mips_id)
    return match.group(1).upper() if match else None


def checked_name(value: str) -> str:
    name = _single_line(value, "name")
    if _title_key(name) in _CMS_TITLES:
        raise PracticeMeasureRejected("this name is a CMS quality measure title; tick that measure in the list instead")
    return name


def checked_identifier(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    identifier = _single_line(value, "identifier")
    if normalise_measure_input(identifier) is not None or is_practice_key(identifier.upper()):
        raise PracticeMeasureRejected("the identifier reads as a measure number; add letters, for example QM-117")
    if _IDENTIFIER.match(identifier) is None:
        raise PracticeMeasureRejected(
            "the identifier may hold only letters, digits, spaces, periods, slashes, hyphens and underscores"
        )
    return identifier


def required_text(value: str, field: str) -> str:
    text = checked_text(value, field)
    if text is None:
        raise PracticeMeasureRejected(f"{field} is empty")
    return text


def checked_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    lines = [_SPACES.sub(" ", line).strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    text = "\n".join(lines).strip()
    if any(not _shown(character) for character in text if character != "\n"):
        raise PracticeMeasureRejected(f"{field} holds characters that cannot be shown")
    return text or None


def checked_codes(met: Iterable[str], not_met: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    met_codes, not_met_codes = _outcome_codes(met), _outcome_codes(not_met)
    both = sorted(set(met_codes) & set(not_met_codes))
    if both:
        raise PracticeMeasureRejected(f"{_echo(both[0])} is listed both when met and when not met")
    return met_codes, not_met_codes


def _outcome_codes(values: Iterable[str]) -> tuple[str, ...]:
    codes: list[str] = []
    for value in values:
        code = _reporting_code(value)
        if code not in codes:
            codes.append(code)
    if len(codes) > CODES_PER_OUTCOME:
        raise PracticeMeasureRejected(f"each outcome takes at most {CODES_PER_OUTCOME} codes")
    return tuple(codes)


def _reporting_code(value: str) -> str:
    text = value.strip().upper().replace(" ", "")
    code, dash, modifier = text.partition("-")
    shaped = CPT_PATTERN.match(code) is not None and (not dash or MODIFIER_PATTERN.match(modifier) is not None)
    if not shaped:
        raise PracticeMeasureRejected(
            f"{_echo(value)} is not a reporting code; use a CPT, CPT Category II or HCPCS code, "
            "with an optional modifier such as 1090F-8P"
        )
    return text


def _single_line(value: str, field: str) -> str:
    text = _SPACES.sub(" ", value.replace("\n", " ").replace("\r", " ")).strip()
    if any(not _shown(character) for character in text):
        raise PracticeMeasureRejected(f"the {field} holds characters that cannot be shown")
    return text


def _shown(character: str) -> bool:
    return unicodedata.category(character)[0] != "C"


def _echo(value: str) -> str:
    text = value.strip()
    if text and len(text) <= _ECHO_LIMIT and text.isprintable():
        return text
    return "that code"


def _title_key(title: str) -> str:
    return " ".join(title.replace("’", "'").split()).rstrip(".").casefold()


_CMS_TITLES = frozenset(
    {_title_key(title) for title, _spec in VERIFIED_MIPS_MEASURES.values()}
    | {_title_key(entry["title"]) for entry in CMS_MIPS_INDEX.values()}
)
