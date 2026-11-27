from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from app.codes.billing_codes import Code

__all__ = [
    "CALENDAR_YEARS",
    "FACILITY_PLACES",
    "NON_FACILITY_PLACES",
    "PAYABLE_STATUSES",
    "PRICE_ADJUSTING_MODIFIERS",
    "ClaimEstimate",
    "FeeDataCorrupt",
    "FeeSchedule",
    "LineEstimate",
    "RateSetting",
    "RelativeValues",
    "fee_schedule_for",
    "load_fee_schedule",
    "rate_setting_for",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
CALENDAR_YEARS = ("2026",)
PAYABLE_STATUSES = frozenset({"A", "R", "T"})
PRICE_ADJUSTING_MODIFIERS = frozenset({"26", "TC", "53", "50", "51", "62", "66", "80", "81", "82", "AS"})
FACILITY_PLACES = frozenset(
    {"02", "19", "21", "22", "23", "24", "26", "31", "34", "41", "42", "51", "52", "53", "56", "61"}
)
NON_FACILITY_PLACES = frozenset(
    {
        *("01", "03", "04", "09", "10", "11", "12", "13", "14", "15", "16", "17", "20", "25", "27"),
        *("32", "33", "49", "50", "54", "55", "57", "58", "60", "62", "65", "71", "72", "81", "99"),
    }
)
CENT = Decimal("0.01")
RateSetting = Literal["facility", "non_facility"]


class FeeDataCorrupt(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RelativeValues:
    code: str
    status: str
    work: Decimal
    pe_non_facility: Decimal
    pe_facility: Decimal
    malpractice: Decimal

    def total(self, setting: RateSetting) -> Decimal:
        practice_expense = self.pe_facility if setting == "facility" else self.pe_non_facility
        return self.work + practice_expense + self.malpractice

    def is_payable(self) -> bool:
        return self.status in PAYABLE_STATUSES and (self.total("facility") > 0 or self.total("non_facility") > 0)


@dataclass(frozen=True, slots=True)
class LineEstimate:
    code: Code
    amount: Decimal | None


@dataclass(frozen=True, slots=True)
class ClaimEstimate:
    release: str
    setting: RateSetting
    lines: tuple[LineEstimate, ...]

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines if line.amount is not None), Decimal("0.00"))

    @property
    def unpriced(self) -> tuple[str, ...]:
        return tuple(line.code.label() for line in self.lines if line.amount is None)


class FeeSchedule:
    def __init__(self, release: str, conversion_factor: Decimal, values: Mapping[str, RelativeValues]) -> None:
        self.release = release
        self.conversion_factor = conversion_factor
        self._values = values

    def relative_values(self, code: str) -> RelativeValues | None:
        return self._values.get(code.strip().upper())

    def unit_amount(self, code: str, setting: RateSetting) -> Decimal | None:
        values = self.relative_values(code)
        if values is None or not values.is_payable():
            return None
        return (values.total(setting) * self.conversion_factor).quantize(CENT, rounding=ROUND_HALF_UP)

    def line(self, code: Code, setting: RateSetting) -> LineEstimate:
        if set(code.modifiers) & PRICE_ADJUSTING_MODIFIERS:
            return LineEstimate(code, None)
        unit = self.unit_amount(code.code, setting)
        return LineEstimate(code, None if unit is None else unit * code.units)

    def estimate(self, codes: Iterable[Code], setting: RateSetting) -> ClaimEstimate:
        lines = tuple(self.line(code, setting) for code in codes if code.type == "CPT")
        return ClaimEstimate(self.release, setting, lines)


def rate_setting_for(place_code: str) -> RateSetting | None:
    if place_code in FACILITY_PLACES:
        return "facility"
    if place_code in NON_FACILITY_PLACES:
        return "non_facility"
    return None


def fee_schedule_for(service_date: date) -> FeeSchedule | None:
    year = str(service_date.year)
    return _schedule(year) if year in CALENDAR_YEARS else None


@cache
def _schedule(year: str) -> FeeSchedule:
    return load_fee_schedule(year)


def load_fee_schedule(year: str, *, data_dir: Path = DATA_DIR) -> FeeSchedule:
    manifest = json.loads((data_dir / f"pfs_rvu_{year}.meta.json").read_text(encoding="utf-8"))
    raw = (data_dir / manifest["artefact"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["artefactSha256"]:
        raise FeeDataCorrupt(f"pfs_rvu_{year} does not match its manifest checksum")
    rows = csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8")), delimiter="\t")
    values = {row["code"]: _relative_values(row) for row in rows}
    payable = sum(1 for item in values.values() if item.is_payable())
    expected = (manifest["totalCodes"], manifest["payableCodes"])
    if (len(values), payable) != expected:
        raise FeeDataCorrupt(
            f"pfs_rvu_{year} has {len(values)} codes ({payable} payable), manifest says {expected[0]} ({expected[1]})"
        )
    return FeeSchedule(manifest["release"], Decimal(manifest["conversionFactor"]), MappingProxyType(values))


def _relative_values(row: Mapping[str, str]) -> RelativeValues:
    return RelativeValues(
        row["code"],
        row["status"],
        Decimal(row["work_rvu"]),
        Decimal(row["pe_rvu_nonfacility"]),
        Decimal(row["pe_rvu_facility"]),
        Decimal(row["mp_rvu"]),
    )
