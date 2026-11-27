from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType

from app.codes.em import EM_FAMILIES, EmFamily

__all__ = [
    "BENCHMARK_FAMILIES",
    "BENCHMARK_YEAR",
    "EmBenchmarkCorrupt",
    "EmBenchmarks",
    "artefact_name",
    "benchmark_family",
    "cms_specialty_for",
    "default_em_benchmarks",
    "load_em_benchmarks",
    "manifest_name",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
BENCHMARK_YEAR = "2025"
BENCHMARK_FAMILIES = (
    "office_new",
    "office_established",
    "nursing_initial",
    "nursing_subsequent",
    "home_new",
    "home_established",
    "inpatient_initial",
    "inpatient_subsequent",
)
COLUMNS = ("specialty", "family", "code", "services")
SPECIALTY_ALIASES = MappingProxyType(
    {
        "family medicine": "FAMILY PRACTICE",
        "general internal medicine": "INTERNAL MEDICINE",
        "pediatrics": "PEDIATRIC MEDICINE",
        "paediatrics": "PEDIATRIC MEDICINE",
        "geriatrics": "GERIATRIC MEDICINE",
        "ob/gyn": "OBSTETRICS/GYNECOLOGY",
        "obgyn": "OBSTETRICS/GYNECOLOGY",
        "obstetrics and gynecology": "OBSTETRICS/GYNECOLOGY",
        "ent": "OTOLARYNGOLOGY",
        "orthopedics": "ORTHOPEDIC SURGERY",
        "orthopaedics": "ORTHOPEDIC SURGERY",
        "pulmonology": "PULMONARY DISEASE",
        "infectious diseases": "INFECTIOUS DISEASE",
        "palliative care": "HOSPICE AND PALLIATIVE CARE",
        "hospice and palliative medicine": "HOSPICE AND PALLIATIVE CARE",
        "pain medicine": "PAIN MANAGEMENT",
        "critical care": "CRITICAL CARE (INTENSIVISTS)",
        "critical care medicine": "CRITICAL CARE (INTENSIVISTS)",
        "plastic surgery": "PLASTIC AND RECONSTRUCTIVE SURGERY",
        "physiatry": "PHYSICAL MEDICINE AND REHABILITATION",
        "pm&r": "PHYSICAL MEDICINE AND REHABILITATION",
        "hematology and oncology": "HEMATOLOGY/ONCOLOGY",
        "hematology oncology": "HEMATOLOGY/ONCOLOGY",
        "oncology": "MEDICAL ONCOLOGY",
        "gynecologic oncology": "GYNECOLOGICAL/ONCOLOGY",
        "colorectal surgery": "COLORECTAL SURGERY (FORMERLY PROCTOLOGY)",
        "allergy and immunology": "ALLERGY/IMMUNOLOGY",
        "nurse practitioner": "NURSE PRACTITIONER",
        "physician assistant": "PHYSICIAN ASSISTANT",
    }
)
_SPACES = re.compile(r"\s+")
_FAMILIES: Mapping[str, EmFamily] = MappingProxyType({family.id: family for family in EM_FAMILIES})


class EmBenchmarkCorrupt(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EmBenchmarks:
    year: str
    source_url: str
    services: Mapping[tuple[str, str], Mapping[str, float]]

    def specialties(self) -> tuple[str, ...]:
        return tuple(sorted({specialty for specialty, _ in self.services}))

    def shares(self, specialty: str, family_id: str) -> Mapping[str, float] | None:
        levels = benchmark_family(family_id).levels
        counts = self.services.get((specialty, family_id))
        total = sum(counts.values()) if counts else 0.0
        if not counts or total <= 0:
            return None
        return MappingProxyType({level.code: counts.get(level.code, 0.0) / total for level in levels})

    def specialty_for(self, text: str | None) -> str | None:
        return cms_specialty_for(text, self.specialties())


def artefact_name(year: str) -> str:
    return f"em_specialty_{year}.tsv.gz"


def manifest_name(year: str) -> str:
    return f"em_specialty_{year}.meta.json"


def benchmark_family(family_id: str) -> EmFamily:
    if family_id not in BENCHMARK_FAMILIES:
        raise KeyError(f"{family_id} is not a benchmarked E/M family")
    return _FAMILIES[family_id]


def cms_specialty_for(text: str | None, known: tuple[str, ...]) -> str | None:
    if not text:
        return None
    plain = _SPACES.sub(" ", text).strip().casefold()
    spelled = _SPACES.sub(" ", plain.replace("&", " and ")).strip()
    by_name = {name.casefold(): name for name in known}
    for key in (plain, spelled):
        found = by_name.get(key) or SPECIALTY_ALIASES.get(key)
        if found in known:
            return found
    return None


def load_em_benchmarks(year: str = BENCHMARK_YEAR, *, data_dir: Path = DATA_DIR) -> EmBenchmarks:
    manifest = json.loads((data_dir / manifest_name(year)).read_text(encoding="utf-8"))
    raw = (data_dir / manifest["artefact"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["artefactSha256"]:
        raise EmBenchmarkCorrupt(f"{manifest_name(year)} does not match the checksum of {manifest['artefact']}")
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8")), delimiter="\t"))
    services = _services(rows, year)
    specialties = {specialty for specialty, _ in services}
    if (len(rows), len(specialties)) != (manifest["rows"], manifest["specialties"]):
        raise EmBenchmarkCorrupt(
            f"em_specialty_{year} has {len(rows)} rows for {len(specialties)} specialties, "
            f"manifest says {manifest['rows']} for {manifest['specialties']}"
        )
    return EmBenchmarks(manifest["calendarYear"], manifest["sourceUrl"], MappingProxyType(services))


@cache
def default_em_benchmarks() -> EmBenchmarks:
    return load_em_benchmarks()


def _services(rows: list[dict[str, str]], year: str) -> dict[tuple[str, str], Mapping[str, float]]:
    found: dict[tuple[str, str], dict[str, float]] = {}
    for row in rows:
        if tuple(row) != COLUMNS:
            raise EmBenchmarkCorrupt(f"em_specialty_{year} columns are {tuple(row)}, expected {COLUMNS}")
        family = benchmark_family(row["family"])
        if row["code"] not in {level.code for level in family.levels}:
            raise EmBenchmarkCorrupt(f"em_specialty_{year}: {row['code']} is not a level of {family.id}")
        found.setdefault((row["specialty"], family.id), {})[row["code"]] = float(row["services"])
    return {key: MappingProxyType(value) for key, value in found.items()}
