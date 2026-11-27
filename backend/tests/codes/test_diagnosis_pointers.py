import pytest

from app.codes.billing_codes import Code, InvalidPointers, parse_code_list, with_pointers


def test_stored_pointers_round_trip_and_older_rows_have_none():
    code = Code("99214", "CPT", ("25",), 1, ("E11.65", "I10"))
    stored = code.as_json()
    assert stored == {"code": "99214", "type": "CPT", "modifiers": ["25"], "units": 1, "pointers": ["E11.65", "I10"]}
    assert Code.from_json(stored) == code
    assert Code("99214", "CPT").as_json() == {"code": "99214", "type": "CPT", "modifiers": [], "units": 1}
    assert Code.from_json({"code": "99214", "type": "CPT", "modifiers": [], "units": 1}).pointers == ()


def test_a_line_points_to_at_most_four_different_diagnoses():
    assert len(Code("99214", "CPT", pointers=("E11.65", "I10", "N18.30", "R20.2")).pointers) == 4
    with pytest.raises(InvalidPointers, match="at most 4"):
        Code("99214", "CPT", pointers=("E11.65", "I10", "N18.30", "R20.2", "Z79.4"))
    with pytest.raises(InvalidPointers, match="same diagnosis twice"):
        Code("99214", "CPT", pointers=("I10", "I10"))


def test_only_procedure_lines_point_and_only_to_diagnosis_codes():
    with pytest.raises(InvalidPointers, match="diagnosis code"):
        Code("I10", "ICD-10", pointers=("E11.65",))
    with pytest.raises(InvalidPointers, match="99213"):
        Code("99214", "CPT", pointers=("99213",))


def test_pointers_join_their_line_and_drop_a_diagnosis_the_claim_lost():
    claim = parse_code_list("99214, 96127x2, E11.65, N18.30").codes
    linked = with_pointers(claim, {"96127": ("N18.30", "I10", "E11.65"), "99215": ("E11.65",)})
    assert linked == (
        Code("99214", "CPT"),
        Code("96127", "CPT", (), 2, ("N18.30", "E11.65")),
        Code("E11.65", "ICD-10"),
        Code("N18.30", "ICD-10"),
    )


def test_an_empty_choice_returns_the_line_to_its_default():
    claim = (Code("99214", "CPT", pointers=("I10",)), Code("I10", "ICD-10"))
    assert with_pointers(claim, {"99214": ()})[0].pointers == ()
