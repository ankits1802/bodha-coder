from app.ai.prompts.context import SYSTEM_INSTRUCTION
from app.ai.review import review_note
from tests.ai.answers import as_text, em_answer, full_answer, patient_answer, review_inputs
from tests.fakes import FakeModelClient


async def test_the_outcome_keeps_each_request_exactly_as_sent() -> None:
    client = FakeModelClient([as_text(full_answer())])

    outcome = await review_note(client, review_inputs())

    assert len(outcome.requests) == len(outcome.replies) == 1
    sent, kept = client.calls[0], outcome.requests[0]
    assert (kept.prompt, kept.schema, kept.system) == (sent.prompt, sent.schema, sent.system)
    assert kept.system == SYSTEM_INSTRUCTION


async def test_a_top_up_call_is_kept_beside_its_reply() -> None:
    client = FakeModelClient(
        [as_text({"patient": patient_answer()}), as_text({"patient": patient_answer(), "em": em_answer()})]
    )

    outcome = await review_note(client, review_inputs(sections=("em",)))

    assert [request.prompt for request in outcome.requests] == [call.prompt for call in client.calls]
    assert [request.schema for request in outcome.requests] == [call.schema for call in client.calls]
    assert len(outcome.replies) == 2
