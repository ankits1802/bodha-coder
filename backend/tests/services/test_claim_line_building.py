from datetime import date

import pytest

from app.codes.billing_codes import Code, parse_code_list
from app.core.errors import Invalid
from app.services.claim_lines import ClaimParty, billing_npi, build_claim, claims_csv

PARTY = ClaimParty("n1", "Ana Ruiz", date(2026, 11, 25), "21", "1234567893", None, "1245319599")
TWELVE = "I10, E11.9, N18.30, E78.5, J44.9, I50.22, K21.9, M17.11, G47.33, F32.A, E66.9, Z79.4"


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
