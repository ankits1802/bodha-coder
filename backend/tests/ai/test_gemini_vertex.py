from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters import gemini
from app.adapters.gemini import (
    INLINE_PDF_LIMIT_BYTES,
    VERTEX_INLINE_PDF_LIMIT_BYTES,
    VERTEX_PDF_TOO_LARGE,
    GeminiClient,
)
from app.ai.errors import ModelNotConfigured, ModelRequestRejected
from app.core.config import Settings
from app.worker import PERMANENT_FAILURES, failure_reason
from tests.ai.test_gemini_adapter import SCHEMA, FakeFiles, FakeModels, answer

PROJECT = "bodha-test"
LOCATION = "us-central1"


def backend_settings(backend: str, **overrides: Any) -> Settings:
    values = {
        "gemini_backend": backend,
        "gemini_api_key": "test-key" if backend == "developer" else None,
        "google_cloud_project": PROJECT,
        "google_cloud_location": LOCATION,
        "gemini_model": "gemini-test",
        "gemini_timeout_seconds": 5,
    }
    return Settings.model_construct(**{**values, **overrides})


def fake_gemini(backend: str, *outcomes: Any) -> tuple[GeminiClient, FakeModels, FakeFiles]:
    models, files = FakeModels(list(outcomes)), FakeFiles()
    fake = SimpleNamespace(aio=SimpleNamespace(models=models, files=files))
    return GeminiClient(backend_settings(backend), client=fake, retry_delay_seconds=0), models, files


class RecordedClient:
    made: list[dict[str, Any]] = []

    def __init__(self, **options: Any) -> None:
        RecordedClient.made.append(options)


@pytest.mark.parametrize("backend", ["developer", "vertex"])
async def test_both_backends_send_a_small_pdf_inline(backend):
    pdf = b"%PDF-1.4 small scan"
    client, models, files = fake_gemini(backend, answer('{"code": "99214"}'))

    reply = await client.generate("review", schema=SCHEMA, pdf=pdf)

    assert reply.text == '{"code": "99214"}'
    document, prompt = models.calls[0]["contents"]
    assert (document.inline_data.data, prompt, files.uploads) == (pdf, "review", 0)


async def test_vertex_sends_a_pdf_above_the_developer_limit_inline():
    pdf = b"%PDF" + b"0" * INLINE_PDF_LIMIT_BYTES
    client, models, files = fake_gemini("vertex", answer("{}"))

    await client.generate("review", schema=SCHEMA, pdf=pdf)

    assert models.calls[0]["contents"][0].inline_data.data == pdf
    assert files.uploads == 0


async def test_vertex_refuses_a_pdf_above_its_inline_limit_for_good():
    pdf = b"%PDF" + b"0" * VERTEX_INLINE_PDF_LIMIT_BYTES
    client, models, files = fake_gemini("vertex", answer("{}"))

    with pytest.raises(ModelRequestRejected) as refused:
        await client.generate("review", schema=SCHEMA, pdf=pdf)

    assert (models.calls, files.uploads) == ([], 0)
    assert isinstance(refused.value, PERMANENT_FAILURES)
    assert failure_reason(refused.value) == VERTEX_PDF_TOO_LARGE == "PDF too large for Vertex inline; split it"


@pytest.mark.parametrize("missing", ["google_cloud_project", "google_cloud_location"])
def test_vertex_needs_a_project_and_a_location(missing):
    with pytest.raises(ModelNotConfigured, match="GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION"):
        GeminiClient(backend_settings("vertex", **{missing: None}))


def test_vertex_builds_the_sdk_client_from_the_project_and_location(monkeypatch):
    RecordedClient.made = []
    monkeypatch.setattr(gemini.genai, "Client", RecordedClient)

    GeminiClient(backend_settings("vertex"))
    GeminiClient(backend_settings("developer"))

    assert RecordedClient.made == [
        {"enterprise": True, "project": PROJECT, "location": LOCATION},
        {"api_key": "test-key"},
    ]
