import json
import shutil
from datetime import date
from decimal import Decimal

import pytest

from app.codes.billing_codes import Code, parse_code_list
from app.codes.fees import DATA_DIR, FeeDataCorrupt, fee_schedule_for, load_fee_schedule, rate_setting_for

SERVICE_DATE = date(2026, 11, 25)


@pytest.fixture(scope="module")
def schedule():
    return load_fee_schedule("2026")


def test_the_release_and_conversion_factor_come_from_the_manifest(schedule):
    assert schedule.release == "RVU26D"
    assert schedule.conversion_factor == Decimal("33.4009")


@pytest.mark.parametrize(
    ("code", "setting", "amount"),
    [
        ("99214", "non_facility", Decimal("135.61")),
        ("99214", "facility", Decimal("84.50")),
        ("99213", "non_facility", Decimal("95.19")),
        ("99215", "non_facility", Decimal("192.39")),
        ("96127", "non_facility", Decimal("5.01")),
        ("G2212", "non_facility", Decimal("34.07")),
        ("99292", "facility", Decimal("100.20")),
    ],
)
def test_the_national_amount_is_the_rvu_total_times_the_conversion_factor(schedule, code, setting, amount):
    assert schedule.unit_amount(code, setting) == amount


@pytest.mark.parametrize("code", ["99417", "3074F", "J1100", "36415", "0054T", "ZZZZZ"])
def test_codes_without_a_national_amount_have_none(schedule, code):
    assert schedule.unit_amount(code, "non_facility") is None


def test_a_claim_estimate_multiplies_units_and_skips_diagnoses(schedule):
    estimate = schedule.estimate(parse_code_list("99214-25, 96127x2, 99417, I10").codes, "non_facility")
    assert [(line.code.label(), line.amount) for line in estimate.lines] == [
        ("99214-25", Decimal("135.61")),
        ("96127 ×2", Decimal("10.02")),
        ("99417", None),
    ]
    assert estimate.total == Decimal("145.63")
    assert estimate.unpriced == ("99417",)


def test_a_modifier_that_changes_the_payment_leaves_the_line_unpriced(schedule):
    estimate = schedule.estimate((Code("99214", "CPT"), Code("20610", "CPT", ("50",))), "non_facility")
    assert [line.amount for line in estimate.lines] == [Decimal("135.61"), None]


@pytest.mark.parametrize(
    ("place", "setting"),
    [("11", "non_facility"), ("12", "non_facility"), ("13", "non_facility"), ("10", "non_facility")]
    + [("32", "non_facility"), ("02", "facility"), ("21", "facility"), ("22", "facility"), ("23", "facility")]
    + [("31", "facility"), ("00", None)],
)
def test_the_place_of_service_picks_the_facility_or_non_facility_rate(place, setting):
    assert rate_setting_for(place) == setting


def test_only_the_vendored_calendar_year_has_a_schedule():
    assert fee_schedule_for(SERVICE_DATE) is not None
    assert fee_schedule_for(date(2025, 12, 31)) is None
    assert fee_schedule_for(date(2027, 1, 1)) is None


def test_a_changed_artefact_is_refused(tmp_path):
    for path in DATA_DIR.glob("pfs_rvu_2026*"):
        shutil.copy(path, tmp_path / path.name)
    artefact = tmp_path / "pfs_rvu_2026.tsv.gz"
    artefact.write_bytes(artefact.read_bytes() + b"\0")

    with pytest.raises(FeeDataCorrupt, match="checksum"):
        load_fee_schedule("2026", data_dir=tmp_path)


def test_a_manifest_with_another_count_is_refused(tmp_path):
    for path in DATA_DIR.glob("pfs_rvu_2026*"):
        shutil.copy(path, tmp_path / path.name)
    manifest_path = tmp_path / "pfs_rvu_2026.meta.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(json.dumps({**manifest, "totalCodes": manifest["totalCodes"] + 1}), encoding="utf-8")

    with pytest.raises(FeeDataCorrupt, match="codes"):
        load_fee_schedule("2026", data_dir=tmp_path)
