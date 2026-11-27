from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib
import io
import json
import re
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HEADER = ["HCPCS CODE", "SPECIALTY", "ALLOWED SERVICES", "ALLOWED CHARGES", "PAYMENT AMOUNT"]
SOURCE_PAGE = (
    "https://www.cms.gov/data-research/statistics-trends-reports/medicare-fee-service-parts-b/"
    "medicare-utilization-part-b/evaluation-management-em-codes-specialty-reports"
)
TRANSFORM = (
    "Rows of the benchmarked E/M families (office new and established, nursing facility initial and "
    "subsequent, home new and established, hospital inpatient or observation initial and subsequent) "
    "with a specialty; allowed services kept as published; rows without a specialty dropped; sorted by "
    "specialty, family and level"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--year", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--page-modified", required=True)
    parser.add_argument("--retrieved-on", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "backend"))
    benchmarks = importlib.import_module("app.codes.em_benchmarks")
    raw = args.workbook.read_bytes()
    rows, dropped = reduce_rows(sheet_rows(raw), benchmarks)
    artefact = gzip.compress(tsv_bytes(rows, benchmarks.COLUMNS), mtime=0)
    manifest = {
        "dataset": "Evaluation and Management (E/M) Codes by Specialty",
        "publisher": "CMS, Medicare Part B Physician/Supplier National Data",
        "calendarYear": args.year,
        "sourcePage": SOURCE_PAGE,
        "sourcePageModified": args.page_modified,
        "sourceUrl": args.source_url,
        "retrievedOn": args.retrieved_on,
        "sourceFileBytes": len(raw),
        "sourceFileSha256": hashlib.sha256(raw).hexdigest(),
        "privacyScreen": "CMS leaves out rows with fewer than 11 allowed services",
        "families": list(benchmarks.BENCHMARK_FAMILIES),
        "transform": TRANSFORM,
        "artefact": benchmarks.artefact_name(args.year),
        "artefactSha256": hashlib.sha256(artefact).hexdigest(),
        "rows": len(rows),
        "specialties": len({row[0] for row in rows}),
        "rowsWithoutSpecialty": dropped,
    }
    (benchmarks.DATA_DIR / manifest["artefact"]).write_bytes(artefact)
    text = json.dumps(manifest, indent=2) + "\n"
    (benchmarks.DATA_DIR / benchmarks.manifest_name(args.year)).write_text(text, encoding="utf-8", newline="\n")
    return 0


def reduce_rows(rows: Iterator[list[str]], benchmarks: ModuleType) -> tuple[list[tuple[str, ...]], int]:
    families = {
        level.code: (family_id, index)
        for family_id in benchmarks.BENCHMARK_FAMILIES
        for index, level in enumerate(benchmarks.benchmark_family(family_id).levels)
    }
    order = {family_id: index for index, family_id in enumerate(benchmarks.BENCHMARK_FAMILIES)}
    kept, dropped, header_seen = [], 0, False
    for row in rows:
        header_seen = header_seen or row[: len(HEADER)] == HEADER
        if not header_seen or len(row) < 3 or row[0] not in families:
            continue
        if not row[1].strip():
            dropped += 1
            continue
        family_id, index = families[row[0]]
        kept.append((row[1].strip(), family_id, row[0], row[2].strip(), order[family_id], index))
    if not header_seen:
        raise ValueError(f"the workbook has no header row {HEADER}")
    kept.sort(key=lambda item: (item[0], item[4], item[5]))
    return [item[:4] for item in kept], dropped


def tsv_bytes(rows: list[tuple[str, ...]], columns: tuple[str, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def sheet_rows(raw: bytes) -> Iterator[list[str]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as book:
        shared = _shared_strings(book)
        sheets = sorted(name for name in book.namelist() if re.match(r"xl/worksheets/[^/]+\.xml$", name))
        for name in sheets:
            for row in ElementTree.fromstring(book.read(name)).iter(f"{SHEET}row"):
                cells = dict(_cell(cell, shared) for cell in row.findall(f"{SHEET}c"))
                yield [cells.get(index, "") for index in range(max(cells, default=-1) + 1)]


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
    return ["".join(part.text or "" for part in item.iter(f"{SHEET}t")) for item in root.findall(f"{SHEET}si")]


def _cell(cell: ElementTree.Element, shared: list[str]) -> tuple[int, str]:
    letters = re.match(r"[A-Z]+", cell.get("r", "A")).group(0)
    column = 0
    for letter in letters:
        column = column * 26 + ord(letter) - 64
    value = cell.find(f"{SHEET}v")
    if cell.get("t") == "inlineStr":
        return column - 1, "".join(part.text or "" for part in cell.iter(f"{SHEET}t"))
    if value is None or value.text is None:
        return column - 1, ""
    return column - 1, shared[int(value.text)] if cell.get("t") == "s" else value.text


if __name__ == "__main__":
    raise SystemExit(main())
