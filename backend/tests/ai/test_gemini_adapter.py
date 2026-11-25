from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from google.genai import errors as genai_errors
from google.genai import types

from app.adapters.gemini import INLINE_PDF_LIMIT_BYTES, GeminiClient, is_transient_error
from app.ai.errors import ModelNotConfigured, ModelRefused, ModelRequestRejected, ModelUnavailable
from app.core.config import Settings

SCHEMA = {"type": "object", "properties": {"code": {"type": "string"}}}
UPLOADED_NAME = "files/scan-1"
UPLOADED_URI = "https://generativelanguage.googleapis.com/v1beta/files/scan-1"
HANG = "hang"


def settings(*, api_key: str | None = "test-key", timeout_seconds: float = 5) -> Settings:
    return Settings.model_construct(
        gemini_api_key=api_key, gemini_model="gemini-test", gemini_timeout_seconds=timeout_seconds
    )


def answer(text: str, *, finish: types.FinishReason = types.FinishReason.STOP) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]), finish_reason=finish)
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=1200, candidates_token_count=300, thoughts_token_count=40
        ),
        model_version="gemini-test-001",
    )


def client_error(code: int) -> genai_errors.ClientError:
    return genai_errors.ClientError(code, {"error": {"code": code, "message": "rejected", "status": "REJECTED"}})


def server_error(code: int) -> genai_errors.ServerError:
    return genai_errors.ServerError(code, {"error": {"code": code, "message": "unavailable", "status": "UNAVAILABLE"}})


@dataclass
class FakeModels:
    outcomes: list[Any]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if outcome == HANG:
            await asyncio.sleep(10)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@dataclass
class FakeFiles:
    uploads: int = 0
    deleted: list[str] = field(default_factory=list)

    async def upload(self, *, file: Any, config: Any) -> types.File:
        self.uploads += 1
        return types.File(name=UPLOADED_NAME, uri=UPLOADED_URI, mime_type=config.mime_type, state="ACTIVE")

    async def delete(self, *, name: str) -> None:
        self.deleted.append(name)


def gemini(*outcomes: Any, timeout_seconds: float = 5) -> tuple[GeminiClient, FakeModels, FakeFiles]:
    models, files = FakeModels(list(outcomes)), FakeFiles()
    fake = SimpleNamespace(aio=SimpleNamespace(models=models, files=files))
    client = GeminiClient(settings(timeout_seconds=timeout_seconds), client=fake, retry_delay_seconds=0)
    return client, models, files


async def test_a_reply_carries_the_text_model_and_usage() -> None:
    client, models, _ = gemini(answer('{"code": "99214"}'))

    reply = await client.generate("review", schema=SCHEMA, system="json only")

    assert (reply.text, reply.model) == ('{"code": "99214"}', "gemini-test-001")
    assert (reply.input_tokens, reply.output_tokens) == (1200, 340)
    config = models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema == SCHEMA
    assert config.system_instruction == "json only"
    assert models.calls[0]["model"] == "gemini-test"


async def test_a_transient_server_error_is_retried() -> None:
    client, models, _ = gemini(server_error(503), answer("{}"))

    reply = await client.generate("review", schema=SCHEMA)

    assert reply.text == "{}"
    assert len(models.calls) == 2


async def test_rate_limits_that_persist_surface_as_model_unavailable() -> None:
    client, models, _ = gemini(client_error(429), client_error(429), client_error(429))

    with pytest.raises(ModelUnavailable):
        await client.generate("review", schema=SCHEMA)
    assert len(models.calls) == 3


async def test_timeouts_are_retried_then_surface_as_model_unavailable() -> None:
    client, models, _ = gemini(HANG, HANG, HANG, timeout_seconds=0.01)

    with pytest.raises(ModelUnavailable):
        await client.generate("review", schema=SCHEMA)
    assert len(models.calls) == 3


async def test_a_rejected_schema_gets_one_unconstrained_retry() -> None:
    client, models, _ = gemini(client_error(400), answer("{}"))

    await client.generate("review", schema=SCHEMA)

    assert len(models.calls) == 2
    assert models.calls[0]["config"].response_schema == SCHEMA
    assert models.calls[1]["config"].response_schema is None
    assert models.calls[1]["config"].response_mime_type == "application/json"


async def test_an_authentication_failure_is_not_retried() -> None:
    client, models, _ = gemini(client_error(401))

    with pytest.raises(ModelRequestRejected):
        await client.generate("review", schema=SCHEMA)
    assert len(models.calls) == 1


async def test_a_safety_stop_is_a_refusal() -> None:
    client, _, _ = gemini(answer("", finish=types.FinishReason.SAFETY))

    with pytest.raises(ModelRefused):
        await client.generate("review", schema=SCHEMA)


async def test_e_a_small_pdf_is_sent_inline_before_the_prompt() -> None:
    pdf = b"%PDF-1.4 small scan"
    client, models, files = gemini(answer("{}"))

    await client.generate("review", schema=SCHEMA, pdf=pdf)

    document, prompt = models.calls[0]["contents"]
    assert (document.inline_data.data, document.inline_data.mime_type) == (pdf, "application/pdf")
    assert prompt == "review"
    assert files.uploads == 0


async def test_e_a_large_pdf_goes_through_the_files_api_and_is_deleted() -> None:
    pdf = b"%PDF" + b"0" * INLINE_PDF_LIMIT_BYTES
    client, models, files = gemini(answer("{}"))

    await client.generate("review", schema=SCHEMA, pdf=pdf)

    document = models.calls[0]["contents"][0]
    assert (document.file_data.file_uri, document.file_data.mime_type) == (UPLOADED_URI, "application/pdf")
    assert files.uploads == 1
    assert files.deleted == [UPLOADED_NAME]


async def test_e_an_upload_is_deleted_even_when_the_call_fails() -> None:
    pdf = b"%PDF" + b"0" * INLINE_PDF_LIMIT_BYTES
    client, _, files = gemini(client_error(403))

    with pytest.raises(ModelRequestRejected):
        await client.generate("review", schema=SCHEMA, pdf=pdf)
    assert files.deleted == [UPLOADED_NAME]


def test_a_missing_api_key_is_a_configuration_error() -> None:
    with pytest.raises(ModelNotConfigured):
        GeminiClient(settings(api_key=None))


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (TimeoutError(), True),
        (ConnectionError(), True),
        (httpx.ConnectError("refused"), True),
        (server_error(500), True),
        (client_error(429), True),
        (client_error(400), False),
        (client_error(401), False),
        (ValueError("bad schema"), False),
        (RuntimeError("bug"), False),
    ],
)
def test_transient_errors_are_told_apart(error: BaseException, transient: bool) -> None:
    assert is_transient_error(error) is transient


async def test_spent_credits_are_named_and_not_retried() -> None:
    client, models, _ = gemini(client_error(402))

    with pytest.raises(ModelRequestRejected, match="no credits left"):
        await client.generate("review", schema=SCHEMA)
    assert len(models.calls) == 1
