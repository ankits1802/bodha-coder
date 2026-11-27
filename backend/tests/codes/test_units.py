import pytest

from app.codes.billing_codes import Code, InvalidUnits, claim_changes, parse_code_list


@pytest.mark.parametrize("text", ["96127x2", "96127 x 2", "96127×2", "96127X2", "96127 ×2"])
def test_units_are_read_in_every_written_form(text):
    assert parse_code_list(text).codes == (Code("96127", "CPT", (), 2),)


def test_units_and_modifiers_are_read_together():
    parsed = parse_code_list("99214-25, 97597-59 x 3")
    assert parsed.codes == (Code("99214", "CPT", ("25",)), Code("97597", "CPT", ("59",), 3))
    assert parsed.invalid == ()


@pytest.mark.parametrize("text", ["96127x0", "96127x100"])
def test_units_outside_one_to_ninety_nine_are_refused(text):
    assert parse_code_list(text).invalid == (text,)


def test_a_hyphenated_x_modifier_is_a_modifier_not_units():
    assert parse_code_list("99214-X2").codes == (Code("99214", "CPT", ("X2",)),)


@pytest.mark.parametrize("text", ["O40.1XX0", "T36.0X1A"])
def test_icd_placeholder_x_is_not_read_as_units(text):
    assert parse_code_list(text).codes == (Code(text, "ICD-10"),)


def test_the_label_shows_units_and_the_typed_form_reads_back():
    code = Code("97597", "CPT", ("59",), 3)
    assert code.label() == "97597-59 ×3"
    assert code.as_text() == "97597-59x3"
    assert parse_code_list(code.as_text()).codes == (code,)
    assert Code("99214", "CPT", ("25",)).label() == "99214-25"


def test_stored_codes_carry_units_and_old_rows_read_as_one_unit():
    code = Code("96127", "CPT", (), 2)
    assert code.as_json() == {"code": "96127", "type": "CPT", "modifiers": [], "units": 2}
    assert Code.from_json(code.as_json()) == code
    assert Code.from_json({"code": "99214", "type": "CPT", "modifiers": ["25"]}) == Code("99214", "CPT", ("25",), 1)


def test_impossible_units_are_refused():
    with pytest.raises(InvalidUnits):
        Code("96127", "CPT", (), 0)
    with pytest.raises(InvalidUnits):
        Code("I10", "ICD-10", (), 2)
    with pytest.raises(InvalidUnits):
        Code.from_json({"code": "96127", "type": "CPT", "modifiers": [], "units": 0})


def test_claim_changes_count_lines_that_differ():
    billed = parse_code_list("99215, 96127, I10").codes
    assert claim_changes(billed, billed) == 0
    assert claim_changes(parse_code_list("99214, 96127, I10").codes, billed) == 2
    assert claim_changes(parse_code_list("99215-25, 96127, I10").codes, billed) == 1
    assert claim_changes(parse_code_list("99215, 96127x2, I10").codes, billed) == 1
    assert claim_changes(parse_code_list("99215, 96127").codes, billed) == 1
