from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "backend" / "app" / "codes" / "data"
MANIFEST = "ncci_practitioner.meta.json"
SCHEMA_VERSION = 1
CMS_FILES = "https://www.cms.gov/files/zip/"
NCCI_PAGES = "https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/"
PTP_PAGE = NCCI_PAGES + "medicare-ncci-procedure-procedure-ptp-edits"
MUE_PAGE = NCCI_PAGES + "medicare-ncci-medically-unlikely-edits-mues"
MUE_ARCHIVE_PAGE = NCCI_PAGES + "medicare-ncci-medically-unlikely-edit-mue-archive"
AOC_PAGE = NCCI_PAGES + "medicare-ncci-add-code-edits"
POLICY_MANUAL = "https://www.cms.gov/files/document/01-chapter1-ncci-medicare-policy-manual-2026-final.pdf"
PTP_PARTS = 4
ACTIVE_INDICATORS = frozenset({"0", "1"})
SOURCE_INDICATORS = frozenset({"0", "1", "9"})
NOT_DELETED = "*"
PTP_HEADER = ("column1", "column2", "effective", "deletion", "modifier")
MUE_HEADER = ("code", "mue", "mai")
AOC_HEADER = ("addon", "primary", "type", "effective", "deletion")
AOC_TYPES = frozenset({"1", "2", "3"})
CONTRACTOR_PRIMARY = "CCCCC"
JULIAN_DAY = re.compile(r"^\d{7}$")
MUE_VALUE_COLUMN = "Practitioner Services MUE Values"
CODE = re.compile(r"^[0-9A-Z]{5}$")
DAY = re.compile(r"^\d{8}$")
MAI = re.compile(r"^([123]) ")
QUARTER = re.compile(r"^(\d{4})Q([1-4])$")
USER_AGENT = "Mozilla/5.0 (compatible; data-fetch)"
DOWNLOAD_SECONDS = 300
CPT_NOTICE = "CPT codes only, copyright American Medical Association; distributed by CMS under the AMA license"


class SourceProblem(ValueError):
    pass


@dataclass(frozen=True)
class Source:
    url: str
    raw: bytes
    member: str
    text: str

    def described(self) -> dict[str, object]:
        return {
            "url": self.url,
            "zipBytes": len(self.raw),
            "zipSha256": sha256(self.raw),
            "file": self.member,
            "fileSha256": sha256(self.text.encode("latin-1")),
        }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quarter_start(label: str) -> date:
    found = QUARTER.match(label)
    if found is None:
        raise SourceProblem(f"{label} is not a quarter such as 2026Q4")
    return date(int(found[1]), 3 * int(found[2]) - 2, 1)


def quarter_end(label: str) -> date:
    start = quarter_start(label)
    following = date(start.year + 1, 1, 1) if start.month == 10 else date(start.year, start.month + 3, 1)
    return following - timedelta(days=1)


def quarter_of(day: date) -> str:
    return f"{day.year}Q{(day.month - 1) // 3 + 1}"


def quarters_between(first: date, last_label: str) -> list[str]:
    labels, cursor = [], first
    while cursor <= quarter_end(last_label):
        labels.append(quarter_of(cursor))
        cursor = quarter_end(quarter_of(cursor)) + timedelta(days=1)
    return labels


def ptp_url(label: str, version: str, part: int) -> str:
    return f"{CMS_FILES}medicare-ncci-{label.lower()}-practitioner-ptp-edits-ccipra-{version}-f{part}.zip"


def mue_url(label: str) -> str:
    year, number = label.split("Q")
    return f"{CMS_FILES}medicare-ncci-{year}-q{number}-practitioner-services-mue-table.zip"


def fetch(url: str, sources: Path | None) -> Source:
    local = sources / url.rsplit("/", 1)[1] if sources else None
    if local is not None and local.is_file():
        raw = local.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=DOWNLOAD_SECONDS) as reply:
            raw = reply.read()
    archive = zipfile.ZipFile(io.BytesIO(raw))
    members = [name for name in archive.namelist() if name.lower().endswith((".txt", ".csv"))]
    if len(members) != 1:
        raise SourceProblem(f"{url} holds {len(members)} text tables, expected one")
    return Source(url, raw, members[0], archive.read(members[0]).decode("latin-1"))


def ptp_rows(source: Source, serves_from: str) -> tuple[list[tuple[str, ...]], int]:
    kept: list[tuple[str, ...]] = []
    records = 0
    for line in source.text.splitlines():
        fields = [field.strip() for field in line.split("\t")]
        if not CODE.match(fields[0]):
            if records:
                raise SourceProblem(f"{source.member} has a row that is not an edit after the header: {line[:60]}")
            continue
        records += 1
        column1, column2, _, effective, deletion, indicator = fields[:6]
        _check_edit(source.member, (column1, column2, effective, deletion, indicator))
        deletion = "" if deletion == NOT_DELETED else deletion
        if indicator in ACTIVE_INDICATORS and (not deletion or deletion >= serves_from):
            kept.append((column1, column2, effective, deletion, indicator))
    return kept, records


def _check_edit(member: str, fields: tuple[str, ...]) -> None:
    column1, column2, effective, deletion, indicator = fields
    valid = (
        CODE.match(column2)
        and DAY.match(effective)
        and (deletion == NOT_DELETED or DAY.match(deletion))
        and indicator in SOURCE_INDICATORS
    )
    if not valid:
        raise SourceProblem(f"{member} has an edit that cannot be read: {column1} {fields[1:]}")


def mue_rows(source: Source) -> list[tuple[str, ...]]:
    rows = list(csv.reader(io.StringIO(source.text)))
    starts = [index for index, row in enumerate(rows) if len(row) > 1 and row[1].strip() == MUE_VALUE_COLUMN]
    if len(starts) != 1:
        raise SourceProblem(f"{source.member} has no single header row naming {MUE_VALUE_COLUMN}")
    kept = []
    for row in (row for row in rows[starts[0] + 1 :] if any(field.strip() for field in row)):
        code, value, indicator = (field.strip() for field in row[:3])
        mai = MAI.match(indicator)
        if not CODE.match(code) or not value.isdigit() or mai is None:
            raise SourceProblem(f"{source.member} has an MUE row that cannot be read: {row[:3]}")
        kept.append((code, str(int(value)), mai[1]))
    if len({row[0] for row in kept}) != len(kept):
        raise SourceProblem(f"{source.member} lists a code twice")
    return sorted(kept)


def aoc_url(label: str) -> str:
    return f"{CMS_FILES}add-code-edits-medicare-effective-{quarter_start(label):%m%d%Y}.zip"


def from_julian(text: str) -> str:
    if not JULIAN_DAY.match(text):
        raise SourceProblem(f"{text} is not a year and day of year")
    return (date(int(text[:4]), 1, 1) + timedelta(days=int(text[4:]) - 1)).strftime("%Y%m%d")


def aoc_rows(source: Source, serves_from: str) -> tuple[list[tuple[str, ...]], int]:
    kept: list[tuple[str, ...]] = []
    lines = [line for line in source.text.splitlines() if line.strip()]
    for line in lines:
        kind, addon, primary = line[0], line[1:6], line[13:18]
        effective, deletion = from_julian(line[25:32]), line[32:39].strip()
        deletion = from_julian(deletion) if deletion else ""
        if kind not in AOC_TYPES or not CODE.match(addon) or not CODE.match(primary):
            raise SourceProblem(f"{source.member} has an add-on edit that cannot be read: {line[:40]}")
        if deletion != effective and (not deletion or deletion >= serves_from):
            kept.append((addon, primary, kind, effective, deletion))
    return sorted(kept), len(lines)


def build_aoc(args: argparse.Namespace, first: date) -> tuple[dict[str, object], bytes]:
    source = fetch(args.aoc_url or aoc_url(args.quarter), args.sources)
    rows, records = aoc_rows(source, first.strftime("%Y%m%d"))
    artefact = tsv_gz(AOC_HEADER, rows)
    described = {
        "effectiveFrom": quarter_start(args.quarter).isoformat(),
        "sourcePage": AOC_PAGE,
        **source.described(),
        "records": records,
        "contractorPrimary": CONTRACTOR_PRIMARY,
        "transform": (
            "add-on code, primary code (CCCCC where the contractor defines the primaries), edit type, effective "
            "and deletion dates converted from year and day of year; edits deleted on their effective date dropped "
            f"(never active); edits deleted before {first.isoformat()} dropped; sorted by add-on, primary"
        ),
        "artefact": f"ncci_aoc_{args.quarter.lower()}.tsv.gz",
        "artefactSha256": sha256(artefact),
        "contentSha256": sha256(gzip.decompress(artefact)),
        "rows": len(rows),
    }
    return described, artefact


def tsv_gz(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> bytes:
    text = "\t".join(header) + "\n" + "".join("\t".join(row) + "\n" for row in rows)
    return gzip.compress(text.encode("ascii"), compresslevel=9, mtime=0)


def build_ptp(args: argparse.Namespace, first: date) -> tuple[dict[str, object], bytes]:
    serves_from = first.strftime("%Y%m%d")
    sources = [fetch(ptp_url(args.quarter, args.ptp_version, part), args.sources) for part in range(1, PTP_PARTS + 1)]
    rows: list[tuple[str, ...]] = []
    parts = []
    for source in sources:
        kept, records = ptp_rows(source, serves_from)
        rows += kept
        parts.append(source.described() | {"records": records})
    rows.sort()
    artefact = tsv_gz(PTP_HEADER, rows)
    name = f"ncci_ptp_{args.quarter.lower()}.tsv.gz"
    described = {
        "version": args.ptp_version,
        "effectiveFrom": quarter_start(args.quarter).isoformat(),
        "sourcePage": PTP_PAGE,
        "sources": parts,
        "sourceRecords": sum(part["records"] for part in parts),
        "transform": (
            "practitioner PTP edits of all parts combined; column 1, column 2, effective date, deletion date "
            "(blank when CMS shows *) and modifier indicator; edits with indicator 9 dropped (never active); "
            f"edits deleted before {first.isoformat()} dropped; sorted by column 1, column 2, effective date"
        ),
        "artefact": name,
        "artefactSha256": sha256(artefact),
        "contentSha256": sha256(gzip.decompress(artefact)),
        "rows": len(rows),
    }
    return described, artefact


def build_mue(args: argparse.Namespace, label: str) -> tuple[dict[str, object], bytes]:
    source = fetch(mue_url(label), args.sources)
    rows = mue_rows(source)
    artefact = tsv_gz(MUE_HEADER, rows)
    described = {
        "quarter": label,
        "effectiveFrom": quarter_start(label).isoformat(),
        "effectiveThrough": quarter_end(label).isoformat(),
        "sourcePage": MUE_PAGE if label == args.quarter else MUE_ARCHIVE_PAGE,
        **source.described(),
        "artefact": f"ncci_mue_{label.lower()}.tsv.gz",
        "artefactSha256": sha256(artefact),
        "contentSha256": sha256(gzip.decompress(artefact)),
        "rows": len(rows),
    }
    return described, artefact


def build(args: argparse.Namespace) -> dict[str, object]:
    first = date.fromisoformat(args.serves_from)
    ptp, ptp_artefact = build_ptp(args, first)
    aoc, aoc_artefact = build_aoc(args, first)
    artefacts = {str(ptp["artefact"]): ptp_artefact, str(aoc["artefact"]): aoc_artefact}
    mues = []
    for label in quarters_between(first, args.quarter):
        described, artefact = build_mue(args, label)
        mues.append(described)
        artefacts[str(described["artefact"])] = artefact
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "program": "Medicare NCCI, practitioner services",
        "quarter": args.quarter,
        "retrievedOn": args.retrieved_on,
        "servesFrom": first.isoformat(),
        "servesThrough": quarter_end(args.quarter).isoformat(),
        "deletionDate": "the last date of service the edit applies to",
        "policyManual": POLICY_MANUAL,
        "license": CPT_NOTICE,
        "ptp": ptp,
        "aoc": aoc,
        "mue": mues,
    }
    write(args.out, manifest, artefacts)
    return manifest


def write(out: Path, manifest: dict[str, object], artefacts: dict[str, bytes]) -> None:
    for stale in out.glob("ncci_*.tsv.gz"):
        if stale.name not in artefacts:
            stale.unlink()
    for name, artefact in artefacts.items():
        (out / name).write_bytes(artefact)
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarter", required=True)
    parser.add_argument("--ptp-version", required=True)
    parser.add_argument("--serves-from", required=True)
    parser.add_argument("--retrieved-on", default=date.today().isoformat())
    parser.add_argument("--aoc-url")
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    manifest = build(parse_args(argv))
    ptp = manifest["ptp"]
    sys.stdout.write(f"{manifest['quarter']}: {ptp['rows']} PTP edits of {ptp['sourceRecords']}, ")
    sys.stdout.write(f"{manifest['aoc']['rows']} add-on edits, {len(manifest['mue'])} MUE quarters, ")
    sys.stdout.write(f"serving {manifest['servesFrom']} to {manifest['servesThrough']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
