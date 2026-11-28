from __future__ import annotations

import json
import re

import pytest

from app.ai.prompts.payer import payer_from_record, payer_record, reads_alike
from app.ai.review import PROMPT_VERSION, review_note
from app.codes.payer_rules import Payer
from tests.ai.answers import as_text, em_answer, patient_answer, review_inputs
from tests.fakes import FakeModelClient

CONTEXT = re.compile(r"# ENCOUNTER CONTEXT\n.*?\n(\{.*?\n\})\n", re.S)


async def _prompt(payer: Payer | None) -> str:
    client = FakeModelClient([as_text({"patient": patient_answer(), "em": em_answer()})])
    await review_note(client, review_inputs(sections=("em",), payer=payer))
    return client.calls[0].prompt


def _context(prompt: str) -> dict:
    found = CONTEXT.search(prompt)
    assert found is not None
    return json.loads(found[1])


def test_the_prompt_version_moved_with_the_payer_context():
    assert PROMPT_VERSION == "2026.11.8"


async def test_an_unknown_payer_is_null_in_the_context_and_the_steps_apply_as_written():
    prompt = await _prompt(None)

    assert _context(prompt)["payer"] is None
    assert "payer is null when the payer is not known yet" in prompt
    assert "When payer is null the payer is not known yet: apply the steps\nabove as written." in prompt
    assert "Medicare uses G2212 instead, never 99417" in prompt


@pytest.mark.parametrize(
    ("payer", "expected"),
    [
        (Payer("medicare"), {"planType": "medicare", "family": None}),
        (Payer("medicare_advantage"), {"planType": "medicare_advantage", "family": None}),
        (Payer("commercial", "cigna"), {"planType": "commercial", "family": "cigna"}),
        (Payer(None), {"planType": "other", "family": None}),
    ],
)
async def test_a_known_payer_reaches_the_model_as_its_plan_type_and_family(payer, expected):
    prompt = await _prompt(payer)

    assert _context(prompt)["payer"] == expected
    assert prompt.index("# STEP 6: THE PAYER") < prompt.index('# OUTPUT: the "em" object')


async def test_the_payer_step_gives_medicare_g2212_telehealth_places_and_g2211():
    prompt = await _prompt(Payer("medicare"))

    assert 'planType "medicare" (traditional Medicare, Part B):\n- Prolonged service: G2212, never 99417' in prompt
    assert "Suggest 95 only when the place of service is 02, 10, 19 or 22." in prompt
    assert "put G2211 in add_on_codes" in prompt
    assert 'planType "commercial", "medicaid" or "other":\n- Prolonged service: 99417, never G2212.' in prompt


def test_the_read_records_the_payer_and_reads_it_back():
    assert payer_record(None) is None
    assert payer_record(Payer("medicare")) == {"plan_type": "medicare", "family": None}
    assert payer_record(Payer(None)) == {"plan_type": "other", "family": None}
    assert payer_from_record(None) is None
    assert payer_from_record({"plan_type": "commercial", "family": "cigna"}) == Payer("commercial", "cigna")
    assert payer_from_record({"plan_type": "other", "family": None}) == Payer(None)


@pytest.mark.parametrize(
    ("first", "second", "alike"),
    [
        (Payer("commercial"), Payer("medicaid"), True),
        (Payer("commercial"), Payer(None), True),
        (Payer("medicare"), Payer("medicare"), True),
        (Payer("medicare"), Payer("medicare_advantage"), False),
        (Payer("medicare"), Payer("commercial"), False),
        (Payer("commercial"), Payer("commercial", "cigna"), False),
        (None, Payer("commercial"), False),
        (None, None, True),
    ],
)
def test_only_a_payer_change_that_changes_the_guidance_reads_differently(first, second, alike):
    assert reads_alike(first, second) is alike
