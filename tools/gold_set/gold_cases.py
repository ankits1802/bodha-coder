from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.codes.billing_codes import Code, parse_code_list  # noqa: E402

__all__ = [
    "CASES_FILE",
    "CASE_ID",
    "MDM_LEVELS",
    "PAYERS",
    "PAYER_NAMES",
    "SCHEMA_VERSION",
    "VISIT_TYPES",
    "Facility",
    "GoldCase",
    "GoldSet",
    "GoldSetInvalid",
    "Letterhead",
    "Mdm",
    "Patient",
    "Provider",
    "Rationale",
    "Scored",
    "Section",
    "Table",
    "Visit",
    "load_gold_set",
    "parse_gold_set",
]

CASES_FILE = Path(__file__).resolve().with_name("cases.json")
SCHEMA_VERSION = 1
CASE_ID = re.compile(r"^GS-(\d{2})$")
MDM_LEVELS = ("Straightforward", "Low", "Moderate", "High")
PAYERS = ("medicare", "medicaid", "commercial")
PAYER_NAMES = {"medicare": "Medicare Part B", "medicaid": "Medicaid", "commercial": "Commercial PPO"}
VISIT_TYPES = ("New patient", "Established patient")
SEXES = ("female", "male")


class GoldSetInvalid(ValueError):
    pass


@dataclass(frozen=True)
class Letterhead:
    name: str
    address: str
    phone: str


@dataclass(frozen=True)
class Facility:
    name: str
    address: str


@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    credential: str
    specialty: str
    email: str

    @property
    def signature(self) -> str:
        return f"{self.name}, {self.credential}"


@dataclass(frozen=True)
class Table:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Section:
    heading: str
    text: str | None
    table: Table | None


@dataclass(frozen=True)
class Visit:
    service_date: date
    place_of_service: str
    visit_type: str
    provider: str
    payer: str


@dataclass(frozen=True)
class Patient:
    sex: str
    age: int


@dataclass(frozen=True)
class Mdm:
    problems: str
    data: str
    risk: str


@dataclass(frozen=True)
class Scored:
    em: str | None
    icd: tuple[str, ...]
    modifiers: tuple[str, ...]


@dataclass(frozen=True)
class Rationale:
    level: str
    codes: Mapping[str, str]
    modifiers: Mapping[str, str]
    billing: str


@dataclass(frozen=True)
class GoldCase:
    id: str
    title: str
    visit: Visit
    patient: Patient
    sections: tuple[Section, ...]
    billed: tuple[Code, ...]
    expected: tuple[Code, ...]
    scored: Scored
    mdm: Mdm | None
    total_minutes: int | None
    rationale: Rationale

    @property
    def number(self) -> str:
        found = CASE_ID.match(self.id)
        return found[1] if found else self.id

    @property
    def patient_label(self) -> str:
        return f"Synthetic Patient {self.number}"

    @property
    def mrn(self) -> str:
        return f"SYN-00{self.number}-ZZ"

    @property
    def file_name(self) -> str:
        return f"{self.visit.service_date.isoformat()} - SYNTHETIC PATIENT - {self.id}.pdf"

    @property
    def billed_text(self) -> str:
        return ", ".join(code.as_text() for code in self.billed)

    @property
    def expected_text(self) -> str:
        return ", ".join(code.as_text() for code in self.expected)

    def note_text(self) -> str:
        parts = [section.text for section in self.sections if section.text]
        cells = [" ".join(row) for section in self.sections if section.table for row in section.table.rows]
        return "\n".join([*parts, *cells])


@dataclass(frozen=True)
class GoldSet:
    letterhead: Letterhead
    facility: Facility
    providers: Mapping[str, Provider]
    cases: tuple[GoldCase, ...]

    def case(self, case_id: str) -> GoldCase:
        for found in self.cases:
            if found.id == case_id:
                return found
        raise GoldSetInvalid(f"no case {case_id} in the gold set")


def load_gold_set(path: Path = CASES_FILE) -> GoldSet:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise GoldSetInvalid(f"{path.name} is not valid JSON: {error}") from error
    return parse_gold_set(raw)


def parse_gold_set(raw: Any) -> GoldSet:
    top = _fields(raw, "gold set", required=("schemaVersion", "letterhead", "facility", "providers", "cases"))
    if top["schemaVersion"] != SCHEMA_VERSION:
        raise GoldSetInvalid(f"schemaVersion {top['schemaVersion']} is not {SCHEMA_VERSION}")
    letterhead = Letterhead(**_texts(top["letterhead"], "letterhead", ("name", "address", "phone")))
    facility = Facility(**_texts(top["facility"], "facility", ("name", "address")))
    providers = [_provider(item) for item in _list(top["providers"], "providers")]
    cases = tuple(_case(item) for item in _list(top["cases"], "cases"))
    return GoldSet(letterhead, facility, {provider.key: provider for provider in providers}, cases)


def _provider(raw: Any) -> Provider:
    return Provider(**_texts(raw, "provider", ("key", "name", "credential", "specialty", "email")))


def _case(raw: Any) -> GoldCase:
    where = raw.get("id", "a case") if isinstance(raw, dict) else "a case"
    case = _fields(
        raw,
        where,
        required=("id", "title", "visit", "patient", "sections", "billed", "expected", "rationale"),
        optional=("mdm", "total_minutes"),
    )
    expected = _fields(case["expected"], f"{where} expected", required=("claim", "scored"))
    return GoldCase(
        id=_text(case["id"], f"{where} id"),
        title=_text(case["title"], f"{where} title"),
        visit=_visit(case["visit"], where),
        patient=_patient(case["patient"], where),
        sections=tuple(_section(item, where) for item in _list(case["sections"], f"{where} sections")),
        billed=_codes(case["billed"], f"{where} billed"),
        expected=_codes(expected["claim"], f"{where} expected claim"),
        scored=_scored(expected["scored"], where),
        mdm=_mdm(case.get("mdm"), where),
        total_minutes=_minutes(case.get("total_minutes"), where),
        rationale=_rationale(case["rationale"], where),
    )


def _visit(raw: Any, where: str) -> Visit:
    names = ("service_date", "place_of_service", "visit_type", "provider", "payer")
    values = _texts(raw, f"{where} visit", names)
    _choice(values["visit_type"], VISIT_TYPES, f"{where} visit type")
    _choice(values["payer"], PAYERS, f"{where} payer")
    try:
        service_date = date.fromisoformat(values["service_date"])
    except ValueError as error:
        raise GoldSetInvalid(f"{where}: {values['service_date']} is not a date") from error
    return Visit(**{**values, "service_date": service_date})


def _patient(raw: Any, where: str) -> Patient:
    values = _fields(raw, f"{where} patient", required=("sex", "age"))
    _choice(values["sex"], SEXES, f"{where} sex")
    if not isinstance(values["age"], int) or not 0 < values["age"] < 110:
        raise GoldSetInvalid(f"{where}: age {values['age']} is not a whole number of years")
    return Patient(values["sex"], values["age"])


def _section(raw: Any, where: str) -> Section:
    values = _fields(raw, f"{where} section", required=("heading",), optional=("text", "table"))
    text = _text(values["text"], f"{where} section text") if "text" in values else None
    table = _table(values["table"], where) if "table" in values else None
    if text is None and table is None:
        raise GoldSetInvalid(f"{where}: section {values['heading']} has neither text nor a table")
    return Section(_text(values["heading"], f"{where} heading"), text, table)


def _table(raw: Any, where: str) -> Table:
    values = _fields(raw, f"{where} table", required=("columns", "rows"))
    columns = tuple(_text(item, f"{where} column") for item in _list(values["columns"], f"{where} columns"))
    rows = tuple(
        tuple(_text(cell, f"{where} cell") for cell in _list(row, f"{where} row"))
        for row in _list(values["rows"], f"{where} rows")
    )
    if any(len(row) != len(columns) for row in rows):
        raise GoldSetInvalid(f"{where}: every table row needs {len(columns)} cells")
    return Table(columns, rows)


def _codes(raw: Any, where: str) -> tuple[Code, ...]:
    listed = [_text(item, where) for item in _list(raw, where)]
    parsed = parse_code_list(", ".join(listed))
    if parsed.invalid or len(parsed.codes) != len(listed):
        raise GoldSetInvalid(f"{where}: not valid or repeated codes: {', '.join(parsed.invalid) or listed}")
    return parsed.codes


def _scored(raw: Any, where: str) -> Scored:
    values = _fields(raw, f"{where} scored", required=("em", "icd", "modifiers"))
    em = None if values["em"] is None else _text(values["em"], f"{where} scored em")
    icd = tuple(_text(item, f"{where} scored icd") for item in _list(values["icd"], f"{where} scored icd"))
    modifiers = tuple(_text(item, f"{where} modifier") for item in _list(values["modifiers"], f"{where} modifiers"))
    return Scored(em, icd, modifiers)


def _mdm(raw: Any, where: str) -> Mdm | None:
    if raw is None:
        return None
    values = _texts(raw, f"{where} mdm", ("problems", "data", "risk"))
    for element, level in values.items():
        _choice(level, MDM_LEVELS, f"{where} mdm {element}")
    return Mdm(**values)


def _minutes(raw: Any, where: str) -> int | None:
    if raw is None:
        return None
    if not isinstance(raw, int) or raw <= 0:
        raise GoldSetInvalid(f"{where}: total_minutes {raw} is not a positive whole number")
    return raw


def _rationale(raw: Any, where: str) -> Rationale:
    values = _fields(raw, f"{where} rationale", required=("level", "codes", "modifiers", "billing"))
    return Rationale(
        level=_text(values["level"], f"{where} rationale level"),
        codes=_text_map(values["codes"], f"{where} rationale codes"),
        modifiers=_text_map(values["modifiers"], f"{where} rationale modifiers"),
        billing=_text(values["billing"], f"{where} rationale billing"),
    )


def _text_map(raw: Any, where: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise GoldSetInvalid(f"{where} must be an object")
    return {_text(key, where): _text(value, f"{where} {key}") for key, value in raw.items()}


def _fields(raw: Any, where: str, *, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise GoldSetInvalid(f"{where} must be an object")
    missing = [name for name in required if name not in raw]
    unknown = sorted(set(raw) - set(required) - set(optional))
    if missing or unknown:
        raise GoldSetInvalid(f"{where}: missing {missing or 'nothing'}, unknown {unknown or 'nothing'}")
    return raw


def _texts(raw: Any, where: str, names: tuple[str, ...]) -> dict[str, str]:
    values = _fields(raw, where, required=names)
    return {name: _text(values[name], f"{where} {name}") for name in names}


def _text(raw: Any, where: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise GoldSetInvalid(f"{where} must be a non-empty string")
    return raw


def _list(raw: Any, where: str) -> list[Any]:
    if not isinstance(raw, list):
        raise GoldSetInvalid(f"{where} must be a list")
    return raw


def _choice(value: str, allowed: tuple[str, ...], where: str) -> None:
    if value not in allowed:
        raise GoldSetInvalid(f"{where}: {value} is not one of {', '.join(allowed)}")
