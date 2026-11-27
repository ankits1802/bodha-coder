import json

import pytest

from app.adapters.demo_model import DemoImageModel
from app.ai.errors import ModelRefused
from app.ai.signature_check import SIGNATURE_CHECK_VERSION, check_signature_image
from tests.fakes import SIGNATURE_ANSWER, FakeImageModel, signature_png


async def test_a_handwritten_signature_passes_and_its_check_is_recorded():
    model = FakeImageModel(answer={**SIGNATURE_ANSWER, "image_issues": ["blurred", "made_up", "shadow"]})

    verdict = await check_signature_image(model, signature_png())

    assert verdict.refusal is None
    assert verdict.record() == {
        "version": SIGNATURE_CHECK_VERSION,
        "model": "fake-gemini",
        "is_signature": True,
        "contains_other_text": False,
        "multiple_signatures": False,
        "image_issues": ["shadow", "blurred"],
    }
    assert model.images == [signature_png()]


@pytest.mark.parametrize(
    ("change", "refusal"),
    [
        ({"is_signature": False}, "does not look like a handwritten signature"),
        ({"contains_other_text": True}, "crop it to the signature alone"),
        ({"multiple_signatures": True}, "more than one signature"),
    ],
)
async def test_an_image_that_is_not_one_handwritten_signature_is_refused(change, refusal):
    verdict = await check_signature_image(FakeImageModel(answer={**SIGNATURE_ANSWER, **change}), signature_png())
    assert refusal in (verdict.refusal or "")


async def test_an_answer_that_cannot_be_read_is_a_refusal_of_the_model():
    model = FakeImageModel(answer={"is_signature": "maybe"})
    with pytest.raises(ModelRefused):
        await check_signature_image(model, signature_png())


async def test_the_demo_backend_always_gives_the_same_passing_answer():
    first = await check_signature_image(DemoImageModel(), signature_png())
    second = await check_signature_image(DemoImageModel(), b"anything")
    assert first.refusal is None and first.record() == second.record()
    assert json.loads(json.dumps(first.record()))["model"] == "bodha-demo"
