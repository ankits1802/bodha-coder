import pytest

from app.codes.mips_scope import practice_scope
from app.codes.practice_measures import (
    PracticeMeasureDefinition,
    PracticeMeasureRejected,
    checked_codes,
    checked_identifier,
    checked_name,
    checked_text,
    key_for,
    practice_key_in_answer,
    required_text,
)

FOLLOW_UP = PracticeMeasureDefinition(
    key="P001",
    version=2,
    version_id="version-2",
    name="Diabetic foot follow-up",
    identifier="QM-7",
    in_scope="Adults with diabetes seen in the office.",
    out_of_scope=None,
    to_meet="A foot exam result and the follow-up interval.",
)


@pytest.mark.parametrize("title", ["Diabetes: Eye Exam", "  diabetes:   EYE exam. ", "Controlling High Blood Pressure"])
def test_a_cms_measure_title_is_never_a_practice_measure_name(title):
    with pytest.raises(PracticeMeasureRejected, match="CMS quality measure title"):
        checked_name(title)


def test_a_name_is_kept_on_one_line_with_single_spaces():
    assert checked_name("  Diabetic   foot\nfollow-up ") == "Diabetic foot follow-up"


@pytest.mark.parametrize("identifier", ["117", "#117", "MIPS 117", "Quality ID 117", "mips#001", "P001", "p042"])
def test_an_identifier_that_reads_as_a_measure_number_is_refused(identifier):
    with pytest.raises(PracticeMeasureRejected, match="reads as a measure number"):
        checked_identifier(identifier)


@pytest.mark.parametrize("identifier", ["QM-117", "HEDIS/CBP", "Payer 2.1", "CBP_2026"])
def test_an_identifier_of_the_practice_is_kept(identifier):
    assert checked_identifier(identifier) == identifier


def test_an_identifier_may_be_left_out_and_takes_no_punctuation_beyond_the_plain_set():
    assert checked_identifier(None) is None
    assert checked_identifier("   ") is None
    with pytest.raises(PracticeMeasureRejected, match="only letters, digits"):
        checked_identifier("QM;DROP")


def test_reporting_codes_are_cpt_category_ii_hcpcs_or_cpt_with_an_optional_modifier():
    met, not_met = checked_codes([" 1090f-8p", "G8427", "g8427"], ["99213", "3046F"])
    assert met == ("1090F-8P", "G8427")
    assert not_met == ("99213", "3046F")


@pytest.mark.parametrize("code", ["E11.9", "ABCDE", "1090F-8PX", "1090F--8P", "123", "1090F-8P-25"])
def test_anything_else_is_not_a_reporting_code(code):
    with pytest.raises(PracticeMeasureRejected, match="is not a reporting code"):
        checked_codes([code], [])


def test_a_code_cannot_report_both_outcomes_and_each_outcome_takes_four_codes():
    with pytest.raises(PracticeMeasureRejected, match="3046F is listed both when met and when not met"):
        checked_codes(["3046F"], ["3046f"])
    with pytest.raises(PracticeMeasureRejected, match="at most 4 codes"):
        checked_codes(["G8427", "G8428", "G8429", "G8430", "G8431"], [])


def test_text_keeps_its_lines_and_refuses_characters_that_cannot_be_shown():
    assert checked_text("Adults  with diabetes\r\n\tseen in the office ", "in scope") == (
        "Adults with diabetes\nseen in the office"
    )
    assert checked_text("   ", "out of scope") is None
    with pytest.raises(PracticeMeasureRejected, match="in scope holds characters"):
        checked_text("Adults\x00 with diabetes", "in scope")
    with pytest.raises(PracticeMeasureRejected, match="to meet is empty"):
        required_text(" \n ", "to meet")


def test_keys_are_a_p_and_three_digits_and_never_a_cms_number():
    assert key_for(1) == "P001"
    assert key_for(999) == "P999"
    with pytest.raises(PracticeMeasureRejected):
        key_for(1000)


@pytest.mark.parametrize(
    ("mips_id", "key"),
    [("PRACTICE #P007", "P007"), ("practice #p007", "P007"), ("P007", "P007"), ("MIPS #117", None), ("117", None)],
)
def test_the_model_names_a_practice_measure_by_its_key(mips_id, key):
    assert practice_key_in_answer(mips_id) == key


def test_the_scope_holds_cms_ids_and_the_current_practice_measures_apart():
    scope = practice_scope(["226", "P001", "117", "P002"], {"P001": FOLLOW_UP})
    assert scope is not None
    assert scope.measure_ids == ("117", "226")
    assert scope.practice_measures == (FOLLOW_UP,)
    assert scope.retired_ids == ("P002",)
    assert scope.listed_ids == ("117", "226", "P001")
    assert not scope.allows_nothing


def test_a_list_of_only_unknown_practice_keys_allows_nothing():
    scope = practice_scope(["P004"], {})
    assert scope is not None and scope.allows_nothing
    assert scope.retired_ids == ("P004",)
