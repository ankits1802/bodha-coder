import gzip
import hashlib
import json
import shutil
from datetime import date

import pytest

from app.codes.billing_codes import Code, parse_code_list
from app.codes.ncci import DATA_DIR, MANIFEST, NcciDataCorrupt, NcciUnavailable, load_ncci

PTP_ROWS = (
    "11000\t11001\t20200101\t20251231\t1",
    "11000\t11001\t20260101\t\t0",
    "20610\t99214\t20201001\t\t1",
    "20611\t20610\t20150101\t\t1",
    "36415\t36591\t20151001\t\t0",
    "99215\t99214\t20201001\t\t1",
    "U0001\tU0002\t20200101\t\t1",
)
AOC_ROWS = (
    "99292\t99291\t1\t20130401\t",
    "99417\t99215\t1\t20210101\t",
    "G2211\t99214\t1\t20240101\t",
    "G2211\t99349\t1\t20260101\t",
    "0054T\tCCCCC\t2\t20130401\t",
)
MUE_2025Q4 = ("20610\t2\t3", "96127\t3\t3", "J1100\t120\t1")
MUE_2026Q1 = ("20610\t2\t3", "96127\t4\t3", "J1100\t120\t1")
FALL = date(2025, 11, 20)
WINTER = date(2026, 1, 15)


def _gz(header: str, rows: tuple[str, ...]) -> bytes:
    return gzip.compress((header + "\n" + "".join(f"{row}\n" for row in rows)).encode("ascii"), mtime=0)


def _artefact(directory, name: str, header: str, rows: tuple[str, ...]) -> dict[str, object]:
    raw = _gz(header, rows)
    (directory / name).write_bytes(raw)
    return {"artefact": name, "artefactSha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows)}


def _mue(directory, quarter: str, bounds: tuple[str, str], rows: tuple[str, ...]) -> dict[str, object]:
    described = _artefact(directory, f"ncci_mue_{quarter.lower()}.tsv.gz", "code\tmue\tmai", rows)
    return {"quarter": quarter, "effectiveFrom": bounds[0], "effectiveThrough": bounds[1], **described}


def _write_fixture(directory) -> None:
    manifest = {
        "schemaVersion": 1,
        "quarter": "2026Q1",
        "servesFrom": "2025-10-01",
        "servesThrough": "2026-03-31",
        "ptp": _artefact(
            directory, "ncci_ptp_2026q1.tsv.gz", "column1\tcolumn2\teffective\tdeletion\tmodifier", PTP_ROWS
        ),
        "aoc": _artefact(directory, "ncci_aoc_2026q1.tsv.gz", "addon\tprimary\ttype\teffective\tdeletion", AOC_ROWS),
        "mue": [
            _mue(directory, "2025Q4", ("2025-10-01", "2025-12-31"), MUE_2025Q4),
            _mue(directory, "2026Q1", ("2026-01-01", "2026-03-31"), MUE_2026Q1),
        ],
    }
    (directory / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def tables(tmp_path):
    _write_fixture(tmp_path)
    return load_ncci(data_dir=tmp_path)


def _edits(tables, text: str, service_date: date) -> list[dict[str, object]]:
    return [edit.as_json() for edit in tables.claim_edits(parse_code_list(text).codes, service_date)]


def test_a_pair_billed_together_names_column_one_and_column_two(tables):
    assert _edits(tables, "99214, 20610, I10", WINTER) == [
        {"kind": "ptp", "column1": "20610", "column2": "99214", "modifier_allowed": True, "bypassed_by": None}
    ]


def test_modifier_25_on_the_visit_bypasses_an_edit_that_allows_a_modifier(tables):
    [edit] = _edits(tables, "99214-25, 20610", WINTER)
    assert (edit["modifier_allowed"], edit["bypassed_by"]) == (True, "25")


def test_modifier_25_on_a_procedure_does_not_bypass(tables):
    [edit] = _edits(tables, "99214, 20610-25", WINTER)
    assert edit["bypassed_by"] is None


def test_modifier_59_on_either_code_bypasses(tables):
    assert _edits(tables, "20611, 20610-59", WINTER)[0]["bypassed_by"] == "59"
    assert _edits(tables, "20611-XS, 20610", WINTER)[0]["bypassed_by"] == "XS"


def test_different_anatomic_modifiers_bypass_and_the_same_side_does_not(tables):
    assert _edits(tables, "20611-RT, 20610-LT", WINTER)[0]["bypassed_by"] == "LT"
    assert _edits(tables, "20611-RT, 20610-RT", WINTER)[0]["bypassed_by"] is None


def test_indicator_0_cannot_be_bypassed_by_any_modifier(tables):
    assert _edits(tables, "36415, 36591-59", WINTER) == [
        {"kind": "ptp", "column1": "36415", "column2": "36591", "modifier_allowed": False, "bypassed_by": None}
    ]


def test_modifiers_22_76_and_77_are_not_ptp_modifiers(tables):
    assert _edits(tables, "99215, 99214-76", WINTER)[0]["bypassed_by"] is None


def test_an_edit_applies_from_its_effective_date_through_its_deletion_date(tables):
    assert tables.ptp_edit("11000", "11001", date(2025, 12, 31)).modifier_allowed is True
    assert tables.ptp_edit("11000", "11001", date(2026, 1, 1)).modifier_allowed is False
    assert tables.ptp_edit("20610", "99214", date(2020, 9, 30)) is None
    assert tables.ptp_edit("99214", "20610", WINTER) is None


def test_the_first_and_last_rows_of_the_table_are_found(tables):
    assert tables.ptp_edit("11000", "11001", WINTER) is not None
    assert tables.ptp_edit("U0001", "U0002", WINTER) is not None
    assert tables.ptp_edit("00100", "99214", WINTER) is None
    assert tables.ptp_edit("ZZZZZ", "99214", WINTER) is None


def test_units_over_the_mue_of_the_quarter_of_the_date_of_service(tables):
    assert _edits(tables, "96127x4", FALL) == [{"kind": "mue", "code": "96127", "units": 4, "limit": 3, "mai": 3}]
    assert _edits(tables, "96127x4", WINTER) == []
    assert _edits(tables, "96127x5", WINTER) == [{"kind": "mue", "code": "96127", "units": 5, "limit": 4, "mai": 3}]


def test_date_of_service_mue_adds_lines_and_line_mue_checks_each_line(tables):
    by_day = (Code("20610", "CPT", ("RT",)), Code("20610", "CPT", ("LT",), 2))
    assert [edit.as_json() for edit in tables.claim_edits(by_day, WINTER)] == [
        {"kind": "mue", "code": "20610", "units": 3, "limit": 2, "mai": 3}
    ]
    by_line = (Code("J1100", "CPT", (), 60), Code("J1100", "CPT", ("JW",), 70))
    assert tables.claim_edits(by_line, WINTER) == []


def test_an_add_on_without_any_listed_primary_is_an_edit(tables):
    assert _edits(tables, "99292", WINTER) == [{"kind": "aoc", "code": "99292", "primaries": ["99291"]}]
    assert _edits(tables, "99291, 99292", WINTER) == []
    assert _edits(tables, "0054T", WINTER) == []


def test_add_on_primaries_follow_the_date_of_service(tables):
    assert tables.add_on_primaries("G2211", FALL).primaries == {"99214"}
    assert tables.add_on_primaries("G2211", WINTER).primaries == {"99214", "99349"}
    assert _edits(tables, "99349, G2211", FALL) == [{"kind": "aoc", "code": "G2211", "primaries": ["99214"]}]
    assert _edits(tables, "99349, G2211", WINTER) == []
    assert tables.add_on_primaries("99214", WINTER) is None


def test_diagnoses_are_not_checked(tables):
    assert _edits(tables, "I10, E11.9", WINTER) == []


def test_dates_outside_the_loaded_quarters_are_refused(tables):
    with pytest.raises(NcciUnavailable, match="2025-10-01 to 2026-03-31"):
        tables.claim_edits(parse_code_list("99214").codes, date(2026, 4, 1))
    with pytest.raises(NcciUnavailable):
        tables.claim_edits(parse_code_list("99214").codes, date(2025, 9, 30))


def test_a_changed_artefact_is_refused(tmp_path):
    _write_fixture(tmp_path)
    (tmp_path / "ncci_ptp_2026q1.tsv.gz").write_bytes(_gz("column1\tcolumn2\teffective\tdeletion\tmodifier", ()))
    with pytest.raises(NcciDataCorrupt, match="checksum"):
        load_ncci(data_dir=tmp_path)


def test_mue_quarters_must_cover_the_served_dates(tmp_path):
    _write_fixture(tmp_path)
    manifest = json.loads((tmp_path / MANIFEST).read_text(encoding="utf-8"))
    manifest["mue"] = manifest["mue"][1:]
    (tmp_path / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(NcciDataCorrupt, match="do not cover"):
        load_ncci(data_dir=tmp_path)


@pytest.fixture(scope="module")
def cms():
    return load_ncci()


def test_the_vendored_tables_serve_2025q4_through_2026q4(cms):
    assert (cms.quarter, cms.serves_from, cms.serves_through) == ("2026Q4", date(2025, 10, 1), date(2026, 12, 31))


def test_cms_practitioner_edits_and_limits(cms):
    day = date(2026, 11, 25)
    assert cms.ptp_edit("20610", "99214", day).modifier_allowed is True
    assert cms.ptp_edit("99215", "99214", day).modifier_allowed is True
    assert cms.ptp_edit("36415", "36591", day).modifier_allowed is False
    assert cms.ptp_edit("0001U", "0029U", date(2026, 6, 30)) is not None
    assert cms.ptp_edit("0001U", "0029U", date(2026, 7, 1)) is None
    assert (cms.mue_limit("96127", date(2025, 11, 1)).limit, cms.mue_limit("96127", day).limit) == (3, 4)
    assert cms.mue_limit("99214", day).limit == 2
    assert cms.add_on_primaries("99292", day).primaries == {"99291"}
    assert "99349" in cms.add_on_primaries("G2211", date(2026, 1, 1)).primaries
    assert "99349" not in cms.add_on_primaries("G2211", date(2025, 12, 31)).primaries


def test_the_vendored_manifest_lists_every_source_with_its_checksum():
    manifest = json.loads((DATA_DIR / MANIFEST).read_text(encoding="utf-8"))
    assert [part["records"] for part in manifest["ptp"]["sources"]] == [675157, 674914, 675035, 612539]
    assert all(len(part["zipSha256"]) == 64 and len(part["fileSha256"]) == 64 for part in manifest["ptp"]["sources"])
    assert [item["quarter"] for item in manifest["mue"]] == ["2025Q4", "2026Q1", "2026Q2", "2026Q3", "2026Q4"]


def test_the_vendored_artefacts_load_from_a_copy(tmp_path):
    for path in DATA_DIR.glob("ncci_*"):
        shutil.copy(path, tmp_path / path.name)
    assert load_ncci(data_dir=tmp_path).quarter == "2026Q4"
