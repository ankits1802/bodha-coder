from datetime import date

import pytest

from app.codes.billing_codes import Code, parse_code_list
from app.codes.ncci import ncci_tables
from app.core.errors import Invalid
from app.services.claim_lines import (
    ClaimParty,
    add_on_primaries,
    billing_npi,
    build_claim,
    claims_csv,
    pointers_view,
)

PARTY = ClaimParty("n1", "Ana Ruiz", date(2026, 11, 25), "21", "1234567893", None, "1245319599")
TWELVE = "I10, E11.9, N18.30, E78.5, J44.9, I50.22, K21.9, M17.11, G47.33, F32.A, E66.9, Z79.4"


@pytest.fixture(scope="module")
def ncci():
    return ncci_tables()


def _claim(text: str):
    return build_claim(PARTY, parse_code_list(text).codes)


def test_diagnoses_take_letters_in_claim_order_without_the_period():
    claim = _claim("99223, I10, E11.9, N18.30")
    assert claim.diagnoses == ("I10", "E119", "N1830")
    assert claim.lines[0].pointers == ("A", "B", "C")


def test_every_line_points_to_at_most_the_first_four_diagnoses():
    claim = _claim("99291, 99292x2, 36556, I10, E11.9, N18.30, E78.5, J44.9, I50.22")
    assert len(claim.diagnoses) == 6
    assert [(line.number, line.code, line.units, line.pointers) for line in claim.lines] == [
        (1, "99291", 1, ("A", "B", "C", "D")),
        (2, "99292", 2, ("A", "B", "C", "D")),
        (3, "36556", 1, ("A", "B", "C", "D")),
    ]


def test_an_add_on_carries_the_pointers_of_its_primary():
    claim = _claim("99291, 99292, J96.01, R65.21")
    primary, add_on = claim.lines
    assert add_on.pointers == primary.pointers == ("A", "B")


def test_twelve_diagnoses_fit_and_a_thirteenth_is_refused():
    assert len(_claim(f"99223, {TWELVE}").diagnoses) == 12
    with pytest.raises(Invalid, match="13 diagnosis codes"):
        _claim(f"99223, {TWELVE}, R26.81")


def test_a_claim_needs_a_procedure_and_a_diagnosis():
    with pytest.raises(Invalid, match="no diagnosis"):
        _claim("99223")
    with pytest.raises(Invalid, match="no procedure"):
        _claim("I10")


def test_modifiers_and_units_stay_on_their_line():
    claim = build_claim(
        PARTY, (Code("20610", "CPT", ("RT", "59"), 1), Code("J1100", "CPT", (), 10), Code("M17.11", "ICD-10"))
    )
    assert [(line.modifiers, line.units) for line in claim.lines] == [(("RT", "59"), 1), ((), 10)]
    with pytest.raises(Invalid, match="more than 4 modifiers"):
        build_claim(PARTY, (Code("20610", "CPT", ("RT", "59", "XS", "76", "77")), Code("M17.11", "ICD-10")))


@pytest.mark.parametrize(
    ("details", "expected"),
    [
        ({"bills_under": "individual", "group_npi": "1245319599"}, "1234567893"),
        ({"bills_under": "group", "group_npi": "1245319599"}, "1245319599"),
        ({"group_npi": "1245319599"}, "1245319599"),
        ({}, None),
    ],
)
def test_the_billing_npi_comes_from_the_provider_details(details, expected):
    assert billing_npi("1234567893", details) == expected


def test_csv_cells_are_formula_safe():
    party = ClaimParty("n1", "=HYPERLINK(1)", date(2026, 11, 25), "11", None, None, None)
    text = claims_csv([build_claim(party, parse_code_list("99213, I10").codes)])
    assert text.splitlines()[1].startswith("n1,'=HYPERLINK(1),2026-11-25,11,,,,1,99213,")


def test_stored_pointers_become_letters_in_the_order_the_coder_chose():
    codes = (
        Code("99214", "CPT", pointers=("N18.30", "I10")),
        Code("96127", "CPT", (), 2),
        Code("I10", "ICD-10"),
        Code("E11.9", "ICD-10"),
        Code("N18.30", "ICD-10"),
    )
    claim = build_claim(PARTY, codes)
    assert [(line.code, line.pointers) for line in claim.lines] == [("99214", ("C", "A")), ("96127", ("A", "B", "C"))]
    assert claims_csv([claim]).splitlines()[1].split(",")[13:15] == ["1", "CA"]


def test_an_add_on_follows_the_pointers_its_primary_was_given():
    codes = (
        Code("99214", "CPT", pointers=("E11.9",)),
        Code("G2211", "CPT"),
        Code("I10", "ICD-10"),
        Code("E11.9", "ICD-10"),
    )
    claim = build_claim(PARTY, codes, primaries={"G2211": "99214"})
    assert [line.pointers for line in claim.lines] == [("B",), ("B",)]
    assert [line.pointers for line in build_claim(PARTY, codes).lines] == [("B",), ("A", "B")]


def test_an_add_on_with_its_own_pointers_keeps_them():
    codes = (
        Code("99291", "CPT", pointers=("J96.01",)),
        Code("99292", "CPT", pointers=("R65.21",)),
        Code("J96.01", "ICD-10"),
        Code("R65.21", "ICD-10"),
    )
    claim = build_claim(PARTY, codes, primaries={"99292": "99291"})
    assert [line.pointers for line in claim.lines] == [("A",), ("B",)]


def test_a_pointer_to_a_diagnosis_the_claim_lacks_is_refused():
    codes = (Code("99214", "CPT", pointers=("E11.65",)), Code("I10", "ICD-10"))
    with pytest.raises(Invalid, match="E11.65"):
        build_claim(PARTY, codes)


def test_ncci_names_the_primary_of_an_add_on_on_the_claim(ncci):
    codes = parse_code_list("99291, 99292, 99214, G2211, 96127x2, I10").codes
    assert add_on_primaries(ncci, codes, date(2026, 11, 25)) == {"99292": "99291", "G2211": "99214"}
    assert add_on_primaries(ncci, parse_code_list("99292, 96127, I10").codes, date(2026, 11, 25)) == {}


def test_the_pointer_view_marks_which_lines_the_coder_linked():
    codes = (
        Code("99214", "CPT", ("25",)),
        Code("96127", "CPT", (), 2, ("N18.30",)),
        Code("I10", "ICD-10"),
        Code("N18.30", "ICD-10"),
    )
    assert pointers_view(codes, {}) == {
        "diagnoses": [{"code": "I10", "letter": "A"}, {"code": "N18.30", "letter": "B"}],
        "lines": [
            {"code": "99214", "label": "99214-25", "pointers": ["I10", "N18.30"], "stored": False},
            {"code": "96127", "label": "96127 ×2", "pointers": ["N18.30"], "stored": True},
        ],
    }


def test_the_pointer_view_letters_only_the_twelve_diagnoses_a_claim_holds():
    view = pointers_view(parse_code_list(f"99223, {TWELVE}, R26.81").codes, {})
    assert [item["letter"] for item in view["diagnoses"]] == [*"ABCDEFGHIJKL", None]
    assert view["lines"][0]["pointers"] == ["I10", "E11.9", "N18.30", "E78.5"]
