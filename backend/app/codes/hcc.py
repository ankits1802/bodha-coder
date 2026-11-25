from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Literal

__all__ = [
    "HCC_MODEL_NAME",
    "PAYMENT_YEARS",
    "HccCategory",
    "HccDataCorrupt",
    "HccInteraction",
    "HccMapping",
    "HccModel",
    "HccPatient",
    "Segment",
    "age_rule_allows",
    "hcc_model_for",
    "load_hcc_model",
    "payment_year_for",
    "segment_for",
    "sex_code",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
HCC_MODEL_NAME = "CMS-HCC V28"
PAYMENT_YEARS = ("2027",)
AGED_FROM = 65
SCORE_DECIMALS = 3
COUNT_CAP = 10
HEART_ASSIST_HCC = "HCC223"
HEART_FAILURE_HCCS = frozenset({"HCC221", "HCC222", "HCC224", "HCC225", "HCC226"})
Segment = Literal["aged", "disabled"]

SEGMENTS: tuple[Segment, ...] = ("aged", "disabled")

_COMPARISON = re.compile(r"^age\s*(<=|>=|<|>|=)\s*(\d+)$")
_RANGE = re.compile(r"^(\d+)\s*<=\s*age\s*<=\s*(\d+)$")
_SEX_CODES = MappingProxyType({"m": "1", "male": "1", "man": "1", "f": "2", "female": "2", "woman": "2"})


class HccDataCorrupt(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class HccPatient:
    age: int | None
    sex: str | None


@dataclass(frozen=True, slots=True)
class HccMapping:
    hcc: str
    age_rules: tuple[str, ...] = ()
    sex: str | None = None

    def applies_to(self, patient: HccPatient) -> bool:
        if self.sex is not None and self.sex != patient.sex:
            return False
        return all(age_rule_allows(rule, patient.age) for rule in self.age_rules)


@dataclass(frozen=True, slots=True)
class HccCategory:
    hcc: str
    label: str
    factors: Mapping[Segment, float]
    trumps: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HccInteraction:
    name: str
    factors: Mapping[Segment, float]
    terms: tuple[str, ...]


class HccModel:
    def __init__(
        self,
        payment_year: str,
        mappings: Mapping[str, tuple[HccMapping, ...]],
        categories: Mapping[str, HccCategory],
        *,
        counts: Mapping[int, Mapping[Segment, float]],
        interactions: tuple[HccInteraction, ...],
    ) -> None:
        self.payment_year = payment_year
        self._mappings = mappings
        self._categories = categories
        self._counts = counts
        self._interactions = interactions

    def hccs_for(self, icd: str, patient: HccPatient) -> frozenset[str]:
        rows = self._mappings.get(_icd_key(icd), ())
        return frozenset(row.hcc for row in rows if row.applies_to(patient) and row.hcc in self._categories)

    def label(self, hcc: str) -> str:
        return self._categories[hcc].label

    def factor(self, hcc: str, segment: Segment) -> float:
        return self._categories[hcc].factors[segment]

    def payment_hccs(self, hccs: Iterable[str]) -> frozenset[str]:
        present = {hcc for hcc in hccs if hcc in self._categories}
        if HEART_ASSIST_HCC in present and not present & HEART_FAILURE_HCCS:
            present.discard(HEART_ASSIST_HCC)
        trumped = {lower for higher in present for lower in self._categories[higher].trumps}
        return frozenset(present - trumped)

    def is_trumped(self, hcc: str, by: Iterable[str]) -> bool:
        return any(hcc in self._categories[higher].trumps for higher in by if higher in self._categories)

    def score(self, hccs: Iterable[str], segment: Segment) -> float:
        paid = self.payment_hccs(hccs)
        total = sum(self._categories[hcc].factors[segment] for hcc in paid)
        total += sum(item.factors[segment] for item in self._interactions if self._has_terms(item, paid))
        if paid:
            total += self._counts[min(len(paid), COUNT_CAP)][segment]
        return round(total, SCORE_DECIMALS)

    def _has_terms(self, interaction: HccInteraction, paid: frozenset[str]) -> bool:
        groups = {group for hcc in paid for group in self._categories[hcc].groups}
        return all(term in paid or term in groups for term in interaction.terms)


def payment_year_for(service_date: date) -> str:
    return str(service_date.year + 1)


def segment_for(age: int | None) -> Segment | None:
    if age is None:
        return None
    return "aged" if age >= AGED_FROM else "disabled"


def sex_code(sex: str | None) -> str | None:
    return _SEX_CODES.get((sex or "").strip().casefold())


def age_rule_allows(rule: str, age: int | None) -> bool:
    if age is None:
        return False
    within = _RANGE.match(rule)
    if within:
        return int(within[1]) <= age <= int(within[2])
    compared = _COMPARISON.match(rule)
    if compared is None:
        raise HccDataCorrupt(f"unsupported HCC age edit {rule!r}")
    limit = int(compared[2])
    return {"<": age < limit, "<=": age <= limit, ">": age > limit, ">=": age >= limit, "=": age == limit}[compared[1]]


def hcc_model_for(payment_year: str | None, *, data_dir: Path = DATA_DIR) -> HccModel | None:
    if payment_year not in PAYMENT_YEARS:
        return None
    return load_hcc_model(payment_year, data_dir=data_dir)


def load_hcc_model(payment_year: str, *, data_dir: Path = DATA_DIR) -> HccModel:
    manifest = json.loads((data_dir / f"hcc_v28_{payment_year}.meta.json").read_text(encoding="utf-8"))
    model_rows = _artefact_rows(data_dir, manifest["modelArtefact"], manifest["modelSha256"])
    categories = _categories(model_rows)
    counts = _counts(model_rows)
    interactions = _interactions(model_rows)
    mappings = _mappings(_artefact_rows(data_dir, manifest["mappingArtefact"], manifest["mappingSha256"]))
    _check_counts(manifest, categories=len(categories), counts=len(counts), interactions=len(interactions))
    mapped_rows = sum(len(rows) for rows in mappings.values())
    if mapped_rows != manifest["mappingRows"]:
        expected = manifest["mappingRows"]
        raise HccDataCorrupt(f"HCC {payment_year} mapping has {mapped_rows} rows, manifest says {expected}")
    unknown = {row.hcc for rows in mappings.values() for row in rows} - set(categories)
    if unknown:
        raise HccDataCorrupt(f"HCC {payment_year} mapping names categories the model lacks: {sorted(unknown)}")
    return HccModel(payment_year, mappings, categories, counts=counts, interactions=interactions)


def _artefact_rows(data_dir: Path, name: str, checksum: str) -> list[dict[str, str]]:
    raw = (data_dir / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != checksum:
        raise HccDataCorrupt(f"{name} does not match its manifest checksum")
    return list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8")), delimiter="\t"))


def _factors(row: Mapping[str, str]) -> Mapping[Segment, float]:
    return MappingProxyType({segment: float(row[segment]) for segment in SEGMENTS})


def _categories(rows: list[dict[str, str]]) -> Mapping[str, HccCategory]:
    return MappingProxyType(
        {
            row["variable"]: HccCategory(
                row["variable"], row["label"], _factors(row), tuple(row["drops"].split()), tuple(row["groups"].split())
            )
            for row in rows
            if row["kind"] == "hcc"
        }
    )


def _counts(rows: list[dict[str, str]]) -> Mapping[int, Mapping[Segment, float]]:
    return MappingProxyType(
        {int(row["variable"][1:].rstrip("P")): _factors(row) for row in rows if row["kind"] == "count"}
    )


def _interactions(rows: list[dict[str, str]]) -> tuple[HccInteraction, ...]:
    return tuple(
        HccInteraction(row["variable"], _factors(row), tuple(row["terms"].split()))
        for row in rows
        if row["kind"] == "interaction"
    )


def _mappings(rows: list[dict[str, str]]) -> Mapping[str, tuple[HccMapping, ...]]:
    found: dict[str, list[HccMapping]] = {}
    for row in rows:
        rules = tuple(rule for rule in (row["mce_age"], row["age_edit"]) if rule)
        for rule in rules:
            age_rule_allows(rule, 0)
        found.setdefault(row["icd"], []).append(HccMapping(row["hcc"], rules, row["sex_edit"] or None))
    return MappingProxyType({icd: tuple(items) for icd, items in found.items()})


def _check_counts(manifest: Mapping[str, object], **counted: int) -> None:
    keys = {"categories": "categories", "counts": "countVariables", "interactions": "interactions"}
    for name, value in counted.items():
        if value != manifest[keys[name]]:
            raise HccDataCorrupt(f"HCC model has {value} {name}, manifest says {manifest[keys[name]]}")


def _icd_key(code: str) -> str:
    return code.strip().upper().replace(".", "")
