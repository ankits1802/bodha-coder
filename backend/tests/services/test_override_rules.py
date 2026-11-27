import pytest

from app.core.errors import Invalid
from app.services.finding import Finding
from app.services.override_reasons import (
    OverrideReason,
    Reasoned,
    checked_reason,
    departing_choices,
    departs_from_bodha,
    missing_reasons,
    reason_text,
)

LOWER = Finding("em", "em", "lower", "Office visit, moderate", "", "99215", "99214")
REMOVE = Finding("diagnosis", "dx:I10", "remove", "Hypertension", "", "I10")
ADD_DX = Finding("diagnosis", "dx:R20.2", "add", "Tingling", "", None, "R20.2", default_choice="add")
SPECIFY = Finding("diagnosis", "dx:N18.30", "ask", "CKD", "", "N18.30", default_choice="ask")
HCC_QUESTION = Finding("diagnosis", "hcc:E11.65", "ask", "Suspected", "", None, "E11.65", default_choice="ask")
CDI = Finding("cdi_query", "cdi-1", "ask", "Query", "", default_choice="ask")
MODIFIER = Finding("modifier", "modifier:25", "add", "Modifier 25", "", "99214", "99214-25")
SUPPORTED = Finding("diagnosis", "dx:E11.65", "keep", "Diabetes", "", "E11.65", default_choice="keep")


@pytest.mark.parametrize(
    ("finding", "choice", "departs"),
    [
        (LOWER, "keep", True),
        (LOWER, "accept", False),
        (REMOVE, "keep", True),
        (REMOVE, "accept", False),
        (ADD_DX, "skip", True),
        (ADD_DX, "add", False),
        (SPECIFY, "keep", True),
        (SPECIFY, "ask", False),
        (HCC_QUESTION, "skip", False),
        (CDI, "skip", False),
        (MODIFIER, "keep", True),
        (SUPPORTED, "keep", False),
    ],
)
def test_a_choice_departs_only_when_it_turns_down_a_change_or_keeps_a_flagged_billed_code(finding, choice, departs):
    assert departs_from_bodha(finding, choice) is departs


def test_the_departing_choices_of_a_finding_are_listed_from_its_allowed_choices():
    assert departing_choices(LOWER, ("accept", "keep")) == ["keep"]
    assert departing_choices(ADD_DX, ("add", "skip")) == ["skip"]
    assert departing_choices(CDI, ("ask", "skip")) == []


def test_other_needs_a_note_and_every_note_is_at_most_500_characters():
    assert checked_reason("payer_policy", "  ") == OverrideReason("payer_policy", None)
    assert checked_reason("other", " Payer contract 12 ") == OverrideReason("other", "Payer contract 12")
    with pytest.raises(Invalid):
        checked_reason("other", None)
    with pytest.raises(Invalid):
        checked_reason("documentation", "x" * 501)
    with pytest.raises(Invalid):
        checked_reason("hunch", None)


def test_a_departing_decision_without_a_reason_is_missing_and_a_reasoned_one_is_not():
    latest = {
        "em": Reasoned("em", "keep", None),
        "dx:I10": Reasoned("dx:I10", "keep", "payer_policy"),
        "dx:R20.2": Reasoned("dx:R20.2", "add", None),
    }
    assert missing_reasons([LOWER, REMOVE, ADD_DX, CDI], latest) == ["em"]


def test_a_reason_reads_as_its_label_with_the_note():
    assert reason_text("provider_answer", None) == "Provider's answer"
    assert reason_text("other", "Payer contract") == "Other: Payer contract"
    assert reason_text(None, "ignored") is None
