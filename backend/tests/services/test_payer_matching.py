import pytest

from app.services.payer_matching import PayerRef, confident_payer, payer_in
from app.services.upload_matching import CHECK_BELOW, Matched

MEDICARE = PayerRef("p-medicare", "Medicare Part B", "medicare")
MEDICAID = PayerRef("p-medicaid", "Texas Medicaid", "medicaid")
AETNA = PayerRef("p-aetna", "Aetna", "commercial")
AETNA_ADVANTAGE = PayerRef("p-aetna-ma", "Aetna Medicare Advantage", "medicare_advantage")
CIGNA = PayerRef("p-cigna", "Cigna", "commercial")
PAYERS = [MEDICARE, MEDICAID, AETNA, AETNA_ADVANTAGE, CIGNA]


def found(text: str, payers: list[PayerRef] = PAYERS) -> tuple[str | None, float]:
    match = payer_in(text, payers)
    return match.value, match.confidence


@pytest.mark.parametrize(
    "text",
    [
        "Insurance: Medicare Part B",
        "Coverage Medicare Part B Chief complaint",
        "Primary insurance - MEDICARE PART B",
        "Payer: Medicare Part B  Member ID 1EG4TE5MK73",
    ],
)
def test_a_listed_payer_named_after_an_insurance_label_is_applied(text):
    assert found(text) == ("p-medicare", 0.9)


def test_the_longest_listed_name_wins_after_a_label():
    assert found("Insurance: Aetna Medicare Advantage PPO") == ("p-aetna-ma", 0.9)
    assert found("Health plan: Aetna Choice POS II") == ("p-aetna", 0.9)


def test_two_listed_payers_named_alike_name_nobody():
    assert found("Insurance: Aetna / Cigna", [AETNA, CIGNA]) == (None, 0.0)
    assert found("Primary Cigna, secondary Aetna", [AETNA, CIGNA]) == (None, 0.0)


def test_a_labelled_medicare_beneficiary_identifier_names_the_one_medicare_payer():
    assert found("MBI: 1EG4-TE5-MK73") == ("p-medicare", 0.85)
    assert found("Medicare # 1EG4TE5MK73") == ("p-medicare", 0.85)


def test_an_mbi_shape_without_a_label_or_with_letters_mbi_never_uses_is_not_read():
    assert found("Account 1EG4-TE5-MK73") == (None, 0.0)
    assert found("MBI: 1SG4-TE5-MK73") == (None, 0.0)
    assert found("MBI: 1EG4-TE5-MK73", [MEDICARE, PayerRef("p-noridian", "Noridian", "medicare")]) == (None, 0.0)


def test_a_labelled_medicaid_member_id_names_the_one_medicaid_payer():
    assert found("Medicaid ID: 123456789012") == ("p-medicaid", 0.85)


def test_plan_words_after_a_label_only_suggest_the_one_payer_of_that_plan_type():
    assert found("Coverage: Medicare") == ("p-medicare", 0.7)
    assert found("Coverage: Humana Medicare Advantage HMO") == ("p-aetna-ma", 0.7)
    assert found("Coverage: Medicaid managed care") == ("p-medicaid", 0.7)


def test_a_listed_name_anywhere_else_on_page_one_is_only_a_suggestion():
    assert found("Seen today. Her Cigna card is on file.") == ("p-cigna", 0.6)


def test_nothing_about_a_payer_suggests_nothing():
    assert found("Assessment and plan: rest and fluids") == (None, 0.0)
    assert found("Insurance: Medicare Part B", []) == (None, 0.0)


def test_only_a_match_at_or_above_the_threshold_is_applied():
    assert confident_payer(Matched("p-medicare", 0.9)) == "p-medicare"
    assert confident_payer(Matched("p-medicare", CHECK_BELOW)) == "p-medicare"
    assert confident_payer(Matched("p-medicare", 0.7)) is None
    assert confident_payer(Matched(None, 0.0)) is None
