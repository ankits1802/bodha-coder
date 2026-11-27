from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from app.codes.catalog_pfs import CODES as PFS_CODES
from app.codes.em import is_em_code
from app.codes.icd import format_icd, is_icd_shaped

CodeType = Literal["CPT", "ICD-10"]
CPT_PATTERN = re.compile(r"^(\d{4}[0-9A-Z]|[A-Z]\d{4})$")
MODIFIER_PATTERN = re.compile(r"^[0-9A-Z]{2}$")
MAX_MODIFIERS = 4
MIN_UNITS = 1
MAX_UNITS = 99
UNITS_SIGN = "×"
KNOWN_CPT_CODES: frozenset[str] = frozenset(PFS_CODES.split())
_UNITS_SUFFIX = re.compile(r"^(?P<body>.+?)\s*[X×]\s*(?P<units>\d+)$")
_PARTS = re.compile(r"[-\s]+")
_FILENAME_PART_SEPARATOR = re.compile(r"\s+-\s+")
_DATE_FORMATS = (
    re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})$"),
    re.compile(r"^(?P<m>\d{2})-(?P<d>\d{2})-(?P<y>\d{4})$"),
)
_PATIENT_NAME = re.compile(r"^[A-Za-z][A-Za-z' ,.-]{1,80}$")


class InvalidUnits(ValueError):
    pass


@dataclass(frozen=True)
class Code:
    code: str
    type: CodeType
    modifiers: tuple[str, ...] = ()
    units: int = 1

    def __post_init__(self) -> None:
        if not MIN_UNITS <= self.units <= MAX_UNITS:
            raise InvalidUnits(f"{self.code} has {self.units} units; units run from {MIN_UNITS} to {MAX_UNITS}")
        if self.units > 1 and self.type != "CPT":
            raise InvalidUnits(f"{self.code} is a diagnosis code and carries no units")

    def label(self) -> str:
        coded = "-".join((self.code, *self.modifiers))
        return f"{coded} {UNITS_SIGN}{self.units}" if self.units > 1 else coded

    def as_text(self) -> str:
        coded = "-".join((self.code, *self.modifiers))
        return f"{coded}x{self.units}" if self.units > 1 else coded

    def as_json(self) -> dict[str, object]:
        return {"code": self.code, "type": self.type, "modifiers": list(self.modifiers), "units": self.units}

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> Code:
        modifiers = value.get("modifiers") or ()
        units = int(value.get("units", MIN_UNITS))
        code_type: CodeType = "CPT" if value["type"] == "CPT" else "ICD-10"
        return cls(str(value["code"]), code_type, tuple(str(m) for m in modifiers), units)


@dataclass(frozen=True)
class ParsedCodes:
    codes: tuple[Code, ...]
    invalid: tuple[str, ...]


@dataclass(frozen=True)
class FilenameFacts:
    service_date: date | None
    patient_name: str | None
    cpt: str | None


def is_known_cpt(code: str) -> bool:
    return code in KNOWN_CPT_CODES or is_em_code(code)


def parse_code_list(text: str) -> ParsedCodes:
    codes: dict[str, Code] = {}
    invalid: list[str] = []
    for raw in re.split(r"[,;\n]+", text):
        token = raw.strip().upper()
        if not token:
            continue
        parsed = _parse_token(token)
        if parsed is None:
            invalid.append(raw.strip())
        else:
            codes.setdefault(f"{parsed.type}:{parsed.code}", parsed)
    return ParsedCodes(tuple(codes.values()), tuple(invalid))


def _parse_token(token: str) -> Code | None:
    counted = _UNITS_SUFFIX.match(token)
    procedure = _procedure(counted["body"]) if counted else None
    if counted and procedure is not None:
        units = int(counted["units"])
        return Code(procedure.code, "CPT", procedure.modifiers, units) if MIN_UNITS <= units <= MAX_UNITS else None
    procedure = _procedure(token)
    if procedure is not None:
        return procedure
    if _PARTS.search(token):
        return None
    if "." in token and is_icd_shaped(token):
        return Code(format_icd(token), "ICD-10")
    if len(token) == 3 and is_icd_shaped(token):
        return Code(token, "ICD-10")
    return None


def _procedure(text: str) -> Code | None:
    base, *modifiers = _PARTS.split(text)
    if (
        CPT_PATTERN.match(base)
        and len(modifiers) <= MAX_MODIFIERS
        and all(MODIFIER_PATTERN.match(m) for m in modifiers)
    ):
        return Code(base, "CPT", tuple(modifiers))
    return None


def format_code_list(codes: tuple[Code, ...] | list[Code]) -> str:
    return ", ".join(code.label() for code in codes)


def claim_changes(final: Iterable[Code], billed: Iterable[Code]) -> int:
    after = {(code.type, code.code): code for code in final}
    before = {(code.type, code.code): code for code in billed}
    only_one_side = len(after.keys() ^ before.keys())
    altered = sum(
        1
        for key in after.keys() & before.keys()
        if (after[key].modifiers, after[key].units) != (before[key].modifiers, before[key].units)
    )
    return only_one_side + altered


def parse_note_filename(file_name: str) -> FilenameFacts:
    stem = re.sub(r"\.pdf$", "", file_name.strip(), flags=re.IGNORECASE)
    parts = [part.strip() for part in _FILENAME_PART_SEPARATOR.split(stem)]
    service_date = next((found for part in parts if (found := _date_from(part)) is not None), None)
    cpt = next((part.upper() for part in parts if CPT_PATTERN.match(part.upper())), None)
    names = [part for part in parts if _PATIENT_NAME.match(part) and _date_from(part) is None]
    patient_name = names[0].title() if len(parts) >= 3 and names else None
    return FilenameFacts(service_date, patient_name, cpt)


def _date_from(text: str) -> date | None:
    for pattern in _DATE_FORMATS:
        found = pattern.match(text)
        if found:
            try:
                return date(int(found["y"]), int(found["m"]), int(found["d"]))
            except ValueError:
                return None
    return None
