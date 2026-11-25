from datetime import date

import pytest

from app.codes.billing_codes import Code, parse_code_list, parse_note_filename
from app.codes.em import compare_em
from app.codes.icd import IcdReleaseUnavailable, fiscal_year_for, format_icd, load_catalog
from app.codes.npi import is_valid_npi


@pytest.fixture(scope="module")
def icd():
    return load_catalog()


def test_fiscal_year_rolls_over_on_october_first():
    assert fiscal_year_for(date(2026, 9, 30)) == "2026"
    assert fiscal_year_for(date(2026, 10, 1)) == "2027"


def test_release_for_a_date_outside_the_loaded_years_is_refused(icd):
    with pytest.raises(IcdReleaseUnavailable):
        icd.for_service_date(date(2025, 9, 30))


def test_billable_and_category_codes_come_from_the_cdc_release(icd):
    release = icd.for_service_date(date(2026, 11, 25))
    assert release.release == "2027"
    assert release.get("I12.9").billable is True
    assert release.get("E11").billable is False
    assert release.get("e1165").description == "Type 2 diabetes mellitus with hyperglycemia"


def test_more_specific_codes_are_billable_descendants(icd):
    release = icd.for_service_date(date(2026, 11, 25))
    codes = [entry.code for entry in release.more_specific("E11.6")]
    assert "E11.65" in codes
    assert "E11.6" not in codes
    assert all(release.get(code).billable for code in codes)


def test_unspecified_codes_are_recognised_from_their_description(icd):
    release = icd.for_service_date(date(2026, 11, 25))
    assert release.is_unspecified("N18.30") is True
    assert release.is_unspecified("N18.32") is False


def test_icd_codes_are_written_with_the_dot():
    assert format_icd("e1165") == "E11.65"
    assert format_icd("I10") == "I10"


def test_code_lists_split_cpt_modifiers_and_icd_codes():
    parsed = parse_code_list("99214-25, I10; E11.65\n99214")
    assert parsed.codes == (Code("99214", "CPT", ("25",)), Code("I10", "ICD-10"), Code("E11.65", "ICD-10"))
    assert parsed.invalid == ()


def test_malformed_codes_are_reported_not_dropped():
    assert parse_code_list("9921, I10").invalid == ("9921",)


def test_filenames_give_date_patient_and_visit_code():
    facts = parse_note_filename("2026-11-25 - REYES MARISOL - 99215 - Progress.pdf")
    assert facts.service_date == date(2026, 11, 25)
    assert facts.patient_name == "Reyes Marisol"
    assert facts.cpt == "99215"


def test_filenames_without_the_pattern_give_nothing():
    facts = parse_note_filename("scan_0042.pdf")
    assert (facts.service_date, facts.patient_name, facts.cpt) == (None, None, None)


@pytest.mark.parametrize(
    ("billed", "supported", "direction", "difference"),
    [
        ("99215", "99214", "lower", 1),
        ("99310", "99308", "lower", 2),
        ("99349", "99350", "raise", -1),
        ("99214", "99214", "keep", 0),
        ("99213", "99204", "replace", 0),
        (None, "99214", "add", 0),
        ("99214", None, "not_applicable", 0),
    ],
)
def test_em_levels_compare_only_within_one_family(billed, supported, direction, difference):
    comparison = compare_em(billed, supported)
    assert comparison.direction == direction
    assert comparison.level_difference == difference


def test_npi_check_digit_follows_the_luhn_rule_with_the_80840_prefix():
    assert is_valid_npi("1234567893") is True
    assert is_valid_npi("1234567890") is False
    assert is_valid_npi("12345") is False
