from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from app.codes.billing_codes import Code
from app.codes.em import is_em_code

__all__ = [
    "ANATOMIC_MODIFIERS",
    "LINE_LEVEL_MAI",
    "PROCEDURE_PTP_MODIFIERS",
    "VISIT_PTP_MODIFIERS",
    "AddOnEdit",
    "AddOnPrimaries",
    "ClaimEdit",
    "MueLimit",
    "NcciDataCorrupt",
    "NcciTables",
    "NcciUnavailable",
    "PairEdit",
    "PtpEdit",
    "UnitsEdit",
    "claim_edits",
    "load_ncci",
    "ncci_tables",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
MANIFEST = "ncci_practitioner.meta.json"
SCHEMA_VERSION = 1
PTP_HEADER = "column1\tcolumn2\teffective\tdeletion\tmodifier"
AOC_HEADER = "addon\tprimary\ttype\teffective\tdeletion"
MUE_HEADER = "code\tmue\tmai"
CODE_LENGTH = 5
MODIFIER_ALLOWED = "1"
INDICATORS = frozenset({"0", "1"})
CONTRACTOR_PRIMARY = "CCCCC"
EVERY_PRIMARY_LISTED = "1"
AOC_TYPES = frozenset({"1", "2", "3"})
MAI_VALUES = frozenset({"1", "2", "3"})
LINE_LEVEL_MAI = 1
ANATOMIC_MODIFIERS = frozenset(
    {
        *("E1", "E2", "E3", "E4", "FA", "TA", "LT", "RT", "LC", "LD", "RC", "LM", "RI"),
        *(f"F{digit}" for digit in range(1, 10)),
        *(f"T{digit}" for digit in range(1, 10)),
    }
)
VISIT_PTP_MODIFIERS = frozenset({"24", "25", "57"})
PROCEDURE_PTP_MODIFIERS = frozenset({"27", "58", "59", "78", "79", "91", "XE", "XP", "XS", "XU"})
_DAY_FORMAT = "%Y%m%d"


class NcciDataCorrupt(ValueError):
    pass


class NcciUnavailable(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class PtpEdit:
    column1: str
    column2: str
    effective: date
    deletion: date | None
    modifier_allowed: bool

    def applies_on(self, service_date: date) -> bool:
        return _in_effect(self.effective, self.deletion, service_date)


@dataclass(frozen=True, slots=True)
class AddOnRow:
    primary: str | None
    every_primary_listed: bool
    effective: date
    deletion: date | None


@dataclass(frozen=True, slots=True)
class AddOnPrimaries:
    code: str
    primaries: frozenset[str]
    every_primary_listed: bool


@dataclass(frozen=True, slots=True)
class MueLimit:
    code: str
    limit: int
    mai: int


@dataclass(frozen=True, slots=True)
class MueQuarter:
    quarter: str
    starts: date
    ends: date
    limits: Mapping[str, MueLimit]


@dataclass(frozen=True, slots=True)
class PairEdit:
    column1: str
    column2: str
    modifier_allowed: bool
    bypassed_by: str | None
    kind: Literal["ptp"] = "ptp"

    def as_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "column1": self.column1,
            "column2": self.column2,
            "modifier_allowed": self.modifier_allowed,
            "bypassed_by": self.bypassed_by,
        }


@dataclass(frozen=True, slots=True)
class UnitsEdit:
    code: str
    units: int
    limit: int
    mai: int
    kind: Literal["mue"] = "mue"

    def as_json(self) -> dict[str, object]:
        return {"kind": self.kind, "code": self.code, "units": self.units, "limit": self.limit, "mai": self.mai}


@dataclass(frozen=True, slots=True)
class AddOnEdit:
    code: str
    primaries: tuple[str, ...]
    kind: Literal["aoc"] = "aoc"

    def as_json(self) -> dict[str, object]:
        return {"kind": self.kind, "code": self.code, "primaries": list(self.primaries)}


ClaimEdit = PairEdit | UnitsEdit | AddOnEdit


class NcciTables:
    def __init__(
        self, quarter: str, ptp_rows: str, add_ons: Mapping[str, tuple[AddOnRow, ...]], mue: tuple[MueQuarter, ...]
    ) -> None:
        if not mue:
            raise NcciDataCorrupt(f"NCCI {quarter} has no MUE quarter")
        self.quarter = quarter
        self.serves_from = mue[0].starts
        self.serves_through = mue[-1].ends
        self._rows = ptp_rows
        self._add_ons = add_ons
        self._mue = mue

    def covers(self, service_date: date) -> bool:
        return self.serves_from <= service_date <= self.serves_through

    def ptp_edit(self, column1: str, column2: str, service_date: date) -> PtpEdit | None:
        return next(
            (edit for edit in self._edits_from(column1) if edit.column2 == column2 and edit.applies_on(service_date)),
            None,
        )

    def add_on_primaries(self, code: str, service_date: date) -> AddOnPrimaries | None:
        rows = [row for row in self._add_ons.get(code, ()) if _in_effect(row.effective, row.deletion, service_date)]
        if not rows:
            return None
        primaries = frozenset(row.primary for row in rows if row.primary is not None)
        return AddOnPrimaries(code, primaries, all(row.every_primary_listed for row in rows))

    def mue_limit(self, code: str, service_date: date) -> MueLimit | None:
        return self._mue_quarter(service_date).limits.get(code)

    def claim_edits(self, codes: tuple[Code, ...], service_date: date) -> list[ClaimEdit]:
        if not self.covers(service_date):
            raise NcciUnavailable(
                f"NCCI edits {self.quarter} cover dates of service {self.serves_from} to {self.serves_through}, "
                f"not {service_date}"
            )
        lines = tuple(code for code in codes if code.type == "CPT")
        pairs = self._pair_edits(lines, service_date)
        return [*pairs, *self._add_on_edits(lines, service_date), *self._units_edits(lines, service_date)]

    def _pair_edits(self, lines: tuple[Code, ...], service_date: date) -> list[ClaimEdit]:
        found: list[ClaimEdit] = []
        for first in lines:
            billed = {line.code: line for line in lines if line.code != first.code}
            for edit in self._edits_from(first.code):
                second = billed.get(edit.column2)
                if second is not None and edit.applies_on(service_date):
                    found.append(_pair_edit(edit, first, second))
        return found

    def _add_on_edits(self, lines: tuple[Code, ...], service_date: date) -> list[ClaimEdit]:
        billed = {line.code for line in lines}
        found: list[ClaimEdit] = []
        for code in dict.fromkeys(line.code for line in lines):
            rule = self.add_on_primaries(code, service_date)
            if rule is not None and rule.every_primary_listed and not rule.primaries & billed:
                found.append(AddOnEdit(code, tuple(sorted(rule.primaries))))
        return found

    def _units_edits(self, lines: tuple[Code, ...], service_date: date) -> list[ClaimEdit]:
        found: list[ClaimEdit] = []
        for code in dict.fromkeys(line.code for line in lines):
            limit = self.mue_limit(code, service_date)
            if limit is None:
                continue
            same = [line.units for line in lines if line.code == code]
            units = max(same) if limit.mai == LINE_LEVEL_MAI else sum(same)
            if units > limit.limit:
                found.append(UnitsEdit(code, units, limit.limit, limit.mai))
        return found

    def _mue_quarter(self, service_date: date) -> MueQuarter:
        for quarter in self._mue:
            if quarter.starts <= service_date <= quarter.ends:
                return quarter
        raise NcciUnavailable(f"no MUE table is loaded for date of service {service_date}")

    def _edits_from(self, column1: str) -> list[PtpEdit]:
        key = column1.strip().upper()
        if len(key) != CODE_LENGTH:
            return []
        position = _first_row_at_or_after(self._rows, key)
        edits: list[PtpEdit] = []
        while self._rows.startswith(f"{key}\t", position):
            end = self._rows.index("\n", position)
            edits.append(_ptp_edit(self._rows[position:end]))
            position = end + 1
        return edits


def claim_edits(codes: tuple[Code, ...], service_date: date) -> list[ClaimEdit]:
    return ncci_tables().claim_edits(codes, service_date)


@cache
def ncci_tables() -> NcciTables:
    return load_ncci()


def load_ncci(*, data_dir: Path = DATA_DIR) -> NcciTables:
    manifest = json.loads((data_dir / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        raise NcciDataCorrupt(f"{MANIFEST} has schema version {manifest.get('schemaVersion')}, expected 1")
    rows = _verified_rows(data_dir, manifest["ptp"], PTP_HEADER)
    add_ons = _add_ons(_verified_rows(data_dir, manifest["aoc"], AOC_HEADER))
    mue = tuple(_mue_quarter(data_dir, item) for item in manifest["mue"])
    _check_coverage(manifest, mue)
    return NcciTables(manifest["quarter"], rows, add_ons, mue)


def _verified_rows(data_dir: Path, described: Mapping[str, Any], header: str) -> str:
    name = described["artefact"]
    raw = (data_dir / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != described["artefactSha256"]:
        raise NcciDataCorrupt(f"{name} does not match its manifest checksum")
    first, _, rows = gzip.decompress(raw).decode("ascii").partition("\n")
    if first != header:
        raise NcciDataCorrupt(f"{name} starts with {first!r}, expected {header!r}")
    count = rows.count("\n")
    if count != described["rows"] or (rows and not rows.endswith("\n")):
        raise NcciDataCorrupt(f"{name} has {count} rows, manifest says {described['rows']}")
    return rows


def _add_ons(rows: str) -> Mapping[str, tuple[AddOnRow, ...]]:
    grouped: dict[str, list[AddOnRow]] = {}
    for line in rows.splitlines():
        code, primary, kind, effective, deletion = line.split("\t")
        if len(code) != CODE_LENGTH or len(primary) != CODE_LENGTH or kind not in AOC_TYPES:
            raise NcciDataCorrupt(f"add-on row {line!r} cannot be read")
        listed = None if primary == CONTRACTOR_PRIMARY else primary
        ended = _day(deletion) if deletion else None
        grouped.setdefault(code, []).append(AddOnRow(listed, kind == EVERY_PRIMARY_LISTED, _day(effective), ended))
    return MappingProxyType({code: tuple(items) for code, items in grouped.items()})


def _mue_quarter(data_dir: Path, described: Mapping[str, Any]) -> MueQuarter:
    rows = _verified_rows(data_dir, described, MUE_HEADER)
    limits = {limit.code: limit for limit in (_mue_limit(line) for line in rows.splitlines())}
    if len(limits) != described["rows"]:
        raise NcciDataCorrupt(f"{described['artefact']} lists a code twice")
    starts, ends = date.fromisoformat(described["effectiveFrom"]), date.fromisoformat(described["effectiveThrough"])
    return MueQuarter(described["quarter"], starts, ends, MappingProxyType(limits))


def _check_coverage(manifest: Mapping[str, Any], mue: tuple[MueQuarter, ...]) -> None:
    contiguous = all((later.starts - earlier.ends).days == 1 for earlier, later in zip(mue, mue[1:], strict=False))
    bounds = (mue[0].starts.isoformat(), mue[-1].ends.isoformat()) if mue else None
    if not contiguous or bounds != (manifest["servesFrom"], manifest["servesThrough"]):
        raise NcciDataCorrupt(f"the MUE quarters do not cover {manifest['servesFrom']} to {manifest['servesThrough']}")


def _mue_limit(line: str) -> MueLimit:
    code, limit, mai = line.split("\t")
    if len(code) != CODE_LENGTH or not limit.isdigit() or mai not in MAI_VALUES:
        raise NcciDataCorrupt(f"MUE row {line!r} cannot be read")
    return MueLimit(code, int(limit), int(mai))


def _ptp_edit(line: str) -> PtpEdit:
    column1, column2, effective, deletion, indicator = line.split("\t")
    if len(column2) != CODE_LENGTH or indicator not in INDICATORS:
        raise NcciDataCorrupt(f"PTP row {line!r} cannot be read")
    ended = _day(deletion) if deletion else None
    return PtpEdit(column1, column2, _day(effective), ended, indicator == MODIFIER_ALLOWED)


def _day(text: str) -> date:
    return datetime.strptime(text, _DAY_FORMAT).date()


def _in_effect(effective: date, deletion: date | None, service_date: date) -> bool:
    return effective <= service_date and (deletion is None or service_date <= deletion)


def _first_row_at_or_after(rows: str, code: str) -> int:
    low, high = 0, len(rows)
    while low < high:
        middle = _row_start(rows, (low + high) // 2)
        if middle >= high:
            middle = low
        if rows[middle : middle + CODE_LENGTH] < code:
            low = rows.index("\n", middle) + 1
        else:
            high = middle
    return low


def _row_start(rows: str, offset: int) -> int:
    return 0 if offset == 0 else rows.index("\n", offset - 1) + 1


def _pair_edit(edit: PtpEdit, first: Code, second: Code) -> PairEdit:
    bypass = _bypassing_modifier(second, first) if edit.modifier_allowed else None
    return PairEdit(edit.column1, edit.column2, edit.modifier_allowed, bypass)


def _bypassing_modifier(second: Code, first: Code) -> str | None:
    visits = tuple(line for line in (second, first) if is_em_code(line.code))
    if visits:
        return _first_modifier(visits, VISIT_PTP_MODIFIERS)
    return _first_modifier((second, first), PROCEDURE_PTP_MODIFIERS) or _different_site(second, first)


def _first_modifier(lines: tuple[Code, ...], accepted: frozenset[str]) -> str | None:
    return next((modifier for line in lines for modifier in line.modifiers if modifier in accepted), None)


def _different_site(second: Code, first: Code) -> str | None:
    sites = [modifier for modifier in second.modifiers if modifier in ANATOMIC_MODIFIERS]
    other_sites = {modifier for modifier in first.modifiers if modifier in ANATOMIC_MODIFIERS}
    if not sites or not other_sites or other_sites.intersection(sites):
        return None
    return sites[0]
