from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.codes.catalog_pfs import CODES as PFS_CODES
from app.codes.em import is_em_code
from app.codes.icd import format_icd, is_icd_shaped

CodeType = Literal["CPT", "ICD-10"]
CPT_PATTERN = re.compile(r"^(\d{4}[0-9A-Z]|[A-Z]\d{4})$")
MODIFIER_PATTERN = re.compile(r"^[0-9A-Z]{2}$")
MAX_MODIFIERS = 4
KNOWN_CPT_CODES: frozenset[str] = frozenset(PFS_CODES.split())
_FILENAME_PART_SEPARATOR = re.compile(r"\s+-\s+")
_DATE_FORMATS = (
    re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})$"),
    re.compile(r"^(?P<m>\d{2})-(?P<d>\d{2})-(?P<y>\d{4})$"),
)
_PATIENT_NAME = re.compile(r"^[A-Za-z][A-Za-z' ,.-]{1,80}$")


@dataclass(frozen=True)
class Code:
    code: str
    type: CodeType
    modifiers: tuple[str, ...] = ()

    def label(self) -> str:
        return "-".join((self.code, *self.modifiers))

    def as_json(self) -> dict[str, object]:
        return {"code": self.code, "type": self.type, "modifiers": list(self.modifiers)}

    @classmethod
    def from_json(cls, value: dict[str, object]) -> Code:
        modifiers = value.get("modifiers") or ()
        return cls(str(value["code"]), "CPT" if value["type"] == "CPT" else "ICD-10", tuple(str(m) for m in modifiers))


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
    base, *modifiers = re.split(r"[-\s]+", token)
    if (
        CPT_PATTERN.match(base)
        and len(modifiers) <= MAX_MODIFIERS
        and all(MODIFIER_PATTERN.match(m) for m in modifiers)
    ):
        return Code(base, "CPT", tuple(modifiers))
    if not modifiers and "." in token and is_icd_shaped(token):
        return Code(format_icd(token), "ICD-10")
    if not modifiers and len(token) == 3 and is_icd_shaped(token):
        return Code(token, "ICD-10")
    return None


def format_code_list(codes: tuple[Code, ...] | list[Code]) -> str:
    return ", ".join(code.label() for code in codes)


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
