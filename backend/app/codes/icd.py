from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
RELEASES = ("2026", "2027")
FISCAL_YEAR_START_MONTH = 10
_UNDOTTED = re.compile(r"^[A-TV-Z][0-9][0-9A-Z][0-9A-Z]{0,4}$")


class IcdReleaseUnavailable(LookupError):
    pass


class IcdDataCorrupt(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IcdCode:
    code: str
    billable: bool
    description: str
    parent: str | None


def format_icd(code: str) -> str:
    key = code.strip().upper().replace(".", "")
    return f"{key[:3]}.{key[3:]}" if len(key) > 3 else key


def is_icd_shaped(code: str) -> bool:
    return bool(_UNDOTTED.match(code.strip().upper().replace(".", "")))


def fiscal_year_for(service_date: date) -> str:
    year = service_date.year + 1 if service_date.month >= FISCAL_YEAR_START_MONTH else service_date.year
    return str(year)


class IcdRelease:
    def __init__(self, release: str, codes: dict[str, IcdCode]) -> None:
        self.release = release
        self._codes = codes
        self._children: dict[str, list[str]] = {}
        for entry in codes.values():
            if entry.parent:
                self._children.setdefault(entry.parent, []).append(entry.code)

    def get(self, code: str) -> IcdCode | None:
        return self._codes.get(format_icd(code))

    def more_specific(self, code: str) -> list[IcdCode]:
        found: list[IcdCode] = []
        pending = list(self._children.get(format_icd(code), []))
        while pending:
            entry = self._codes[pending.pop()]
            if entry.billable:
                found.append(entry)
            pending.extend(self._children.get(entry.code, []))
        return sorted(found, key=lambda item: item.code)

    def is_unspecified(self, code: str) -> bool:
        entry = self.get(code)
        return entry is not None and "unspecified" in entry.description.casefold()


class IcdCatalog:
    def __init__(self, releases: dict[str, IcdRelease]) -> None:
        self._releases = releases

    def for_service_date(self, service_date: date) -> IcdRelease:
        release = fiscal_year_for(service_date)
        if release not in self._releases:
            raise IcdReleaseUnavailable(f"ICD-10-CM release {release} is not loaded for service date {service_date}")
        return self._releases[release]


def load_release(release: str, *, data_dir: Path = DATA_DIR) -> IcdRelease:
    manifest = json.loads((data_dir / f"icd10cm_{release}.meta.json").read_text(encoding="utf-8"))
    raw = (data_dir / manifest["artefact"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["artefactSha256"]:
        raise IcdDataCorrupt(f"icd10cm_{release} does not match its manifest checksum")
    rows = csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8")), delimiter="\t")
    codes = {
        row["code"]: IcdCode(row["code"], row["billable"] == "1", row["long_desc"], row["parent_code"] or None)
        for row in rows
    }
    if len(codes) != manifest["totalCodes"]:
        raise IcdDataCorrupt(f"icd10cm_{release} has {len(codes)} codes, manifest says {manifest['totalCodes']}")
    return IcdRelease(release, codes)


def load_catalog(*, data_dir: Path = DATA_DIR) -> IcdCatalog:
    return IcdCatalog({release: load_release(release, data_dir=data_dir) for release in RELEASES})
