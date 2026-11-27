from __future__ import annotations

import asyncio
import copy
import io
import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.contracts import ModelReply
from app.ai.errors import ModelError, ModelNotConfigured, ModelRefused, ModelRequestRejected, ModelUnavailable
from app.core.config import Settings

__all__ = [
    "INLINE_PDF_LIMIT_BYTES",
    "VERTEX_INLINE_PDF_LIMIT_BYTES",
    "VERTEX_PDF_TOO_LARGE",
    "GeminiClient",
    "is_transient_error",
    "retry_operation",
]

logger = logging.getLogger(__name__)

TEMPERATURE = 0.2
JSON_MIME_TYPE = "application/json"
PDF_MIME_TYPE = "application/pdf"
INLINE_PDF_LIMIT_BYTES = 14 * 1024 * 1024
VERTEX_INLINE_PDF_LIMIT_BYTES = 50 * 1024 * 1024
VERTEX_PDF_TOO_LARGE = "PDF too large for Vertex inline; split it"
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 1.0
UPLOAD_POLL_SECONDS = 1.0
UPLOAD_POLLS = 30
SERVER_ERROR = 500
BAD_REQUEST = 400
PAYMENT_REQUIRED = 402

_RETRYABLE_STATUS = frozenset({408, 409, 425, 429})
_RETRYABLE_NAMES = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "OverloadedError",
        "ServiceUnavailable",
        "ServerError",
        "TooManyRequests",
        "ResourceExhausted",
        "DeadlineExceeded",
        "Unavailable",
        "TransportError",
    }
)
_TERMINAL_NAMES = frozenset(
    {
        "ValidationError",
        "BadRequestError",
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "UnprocessableEntityError",
        "InvalidArgument",
        "PermissionDenied",
        "NotFound",
        "Unauthenticated",
    }
)
_REFUSAL_FINISH_REASONS = frozenset({"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "MODEL_ARMOR"})
_NOTHING_SEEN: frozenset[int] = frozenset()


class GeminiClient:
    def __init__(
        self,
        settings: Settings,
        *,
        client: Any = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    ) -> None:
        self._vertex = settings.gemini_backend == "vertex"
        self._client = client if client is not None else _sdk_client(settings)
        self._inline_limit = VERTEX_INLINE_PDF_LIMIT_BYTES if self._vertex else INLINE_PDF_LIMIT_BYTES
        self._model = settings.gemini_model
        self._timeout_seconds = float(settings.gemini_timeout_seconds)
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds

    async def aclose(self) -> None:
        await self._client.aio.aclose()

    async def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None,
        pdf: bytes | None = None,
        system: str | None = None,
    ) -> ModelReply:
        async with self._pdf_part(pdf) as document:
            contents: list[Any] = [prompt] if document is None else [document, prompt]
            response = await self._answer(contents, schema=schema, system=system)
        return self._reply(response)

    async def inspect_image(self, prompt: str, *, schema: dict[str, Any], image: bytes, mime_type: str) -> ModelReply:
        picture = types.Part.from_bytes(data=image, mime_type=mime_type)
        return self._reply(await self._answer([picture, prompt], schema=schema, system=None))

    async def _answer(
        self, contents: list[Any], *, schema: dict[str, Any] | None, system: str | None
    ) -> types.GenerateContentResponse:
        if schema is None:
            return await self._generate(contents, _generation_config(system))
        try:
            return await self._generate(contents, _generation_config(system, mime_type=JSON_MIME_TYPE, schema=schema))
        except (ModelRequestRejected, ModelUnavailable) as error:
            if not _schema_may_be_at_fault(error):
                raise
            logger.warning("Gemini schema-constrained call failed (%s); retrying once without the schema", error)
        return await self._generate(contents, _generation_config(system, mime_type=JSON_MIME_TYPE))

    async def _generate(
        self, contents: list[Any], config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse:
        return await self._guarded(
            lambda: self._client.aio.models.generate_content(model=self._model, contents=contents, config=config),
            "generate_content",
        )

    async def _guarded[T](self, operation: Callable[[], Awaitable[T]], name: str) -> T:
        async def bounded() -> T:
            async with asyncio.timeout(self._timeout_seconds):
                return await operation()

        try:
            return await retry_operation(
                bounded, name=name, max_retries=self._max_retries, delay=self._retry_delay_seconds
            )
        except Exception as error:
            translated = _model_error(error, name)
            if translated is None:
                raise
            raise translated from error

    @asynccontextmanager
    async def _pdf_part(self, pdf: bytes | None) -> AsyncIterator[types.Part | None]:
        if pdf is None:
            yield None
            return
        if len(pdf) <= self._inline_limit:
            yield types.Part.from_bytes(data=pdf, mime_type=PDF_MIME_TYPE)
            return
        if self._vertex:
            raise ModelRequestRejected(VERTEX_PDF_TOO_LARGE)
        uploaded = await self._guarded(
            lambda: self._client.aio.files.upload(
                file=io.BytesIO(pdf), config=types.UploadFileConfig(mime_type=PDF_MIME_TYPE)
            ),
            "files.upload",
        )
        try:
            ready = await self._ready(uploaded)
            yield types.Part.from_uri(file_uri=ready.uri, mime_type=PDF_MIME_TYPE)
        finally:
            await self._delete(uploaded.name)

    async def _ready(self, uploaded: types.File) -> types.File:
        for _ in range(UPLOAD_POLLS):
            if uploaded.state != types.FileState.PROCESSING:
                break
            await asyncio.sleep(UPLOAD_POLL_SECONDS)
            uploaded = await self._fetched(uploaded.name)
        if uploaded.state == types.FileState.FAILED:
            raise ModelRequestRejected("Gemini could not process the uploaded PDF.")
        if uploaded.state == types.FileState.PROCESSING or not uploaded.uri:
            raise ModelUnavailable("The uploaded PDF was not ready for Gemini in time.")
        return uploaded

    async def _fetched(self, name: str | None) -> types.File:
        return await self._guarded(lambda: self._client.aio.files.get(name=name), "files.get")

    async def _delete(self, name: str | None) -> None:
        if not name:
            return
        try:
            await self._guarded(lambda: self._client.aio.files.delete(name=name), "files.delete")
        except ModelError as error:
            logger.warning("Gemini did not delete an uploaded PDF (%s); the service expires it after 48 hours", error)

    def _reply(self, response: types.GenerateContentResponse) -> ModelReply:
        _raise_if_refused(response)
        text = response.text
        if text is None or not text.strip():
            raise ModelRefused(f"Gemini returned no answer text (finish reason {_finish_reason(response)}).")
        usage = response.usage_metadata
        if usage is None:
            logger.warning("Gemini returned no usage metadata; the reply records zero tokens")
        return ModelReply(
            text=text,
            model=response.model_version or self._model,
            input_tokens=_tokens(usage, "prompt_token_count"),
            output_tokens=_tokens(usage, "candidates_token_count") + _tokens(usage, "thoughts_token_count"),
        )


def _sdk_client(settings: Settings) -> genai.Client:
    if settings.gemini_backend == "vertex":
        if not settings.google_cloud_project or not settings.google_cloud_location:
            raise ModelNotConfigured(
                "GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set when GEMINI_BACKEND is vertex."
            )
        return genai.Client(
            enterprise=True, project=settings.google_cloud_project, location=settings.google_cloud_location
        )
    if not settings.gemini_api_key:
        raise ModelNotConfigured("GEMINI_API_KEY is not set, so the review model cannot be called.")
    return genai.Client(api_key=settings.gemini_api_key)


async def retry_operation[T](
    operation: Callable[[], Awaitable[T]],
    *,
    name: str,
    max_retries: int,
    delay: float,
    should_retry: Callable[[BaseException], bool] | None = None,
) -> T:
    retryable = should_retry or is_transient_error
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as error:
            if attempt >= max_retries or not retryable(error):
                raise
            logger.warning(
                "model call %s attempt %d of %d failed (%s); retrying",
                name,
                attempt + 1,
                max_retries + 1,
                type(error).__name__,
            )
        await asyncio.sleep(_backoff_delay(delay, attempt))
        attempt += 1


def is_transient_error(error: BaseException) -> bool:
    return _classify(error, _NOTHING_SEEN) is True


def _classify(error: BaseException, seen: frozenset[int]) -> bool | None:
    if id(error) in seen:
        return None
    seen = seen | {id(error)}
    declared = getattr(error, "retryable", None)
    if isinstance(declared, bool):
        return declared
    status = _http_status(error)
    if status is not None:
        return status in _RETRYABLE_STATUS or status >= SERVER_ERROR
    names = {kind.__name__ for kind in type(error).__mro__}
    if names & _TERMINAL_NAMES:
        return False
    if names & _RETRYABLE_NAMES or isinstance(error, (TimeoutError, ConnectionError)):
        return True
    for nested in (error.__cause__, error.__context__):
        verdict = None if nested is None else _classify(nested, seen)
        if verdict is not None:
            return verdict
    return False if isinstance(error, ValueError) else None


def _http_status(error: BaseException) -> int | None:
    for holder in (error, getattr(error, "response", None)):
        if holder is None:
            continue
        for attribute in ("status_code", "status", "code"):
            value = getattr(holder, attribute, None)
            if isinstance(value, int) and 100 <= value < 600:
                return value
    return None


def _backoff_delay(delay: float, attempt: int) -> float:
    return delay * (2**attempt) * (0.5 + random.random() / 2)


def _model_error(error: Exception, name: str) -> ModelError | None:
    status = _http_status(error)
    if is_transient_error(error):
        return ModelUnavailable(f"Gemini {name} failed after retries ({type(error).__name__}).", status=status)
    if isinstance(error, genai_errors.APIError) and error.code == PAYMENT_REQUIRED:
        return ModelRequestRejected("The Gemini account has no credits left (HTTP 402).", status=error.code)
    if isinstance(error, genai_errors.APIError):
        return ModelRequestRejected(f"Gemini rejected {name} (HTTP {error.code}).", status=error.code)
    if isinstance(error, ValueError):
        return ModelRequestRejected(f"Gemini {name} could not be sent ({type(error).__name__}).")
    return None


def _schema_may_be_at_fault(error: ModelError) -> bool:
    if isinstance(error, ModelRequestRejected):
        return error.status is None or error.status == BAD_REQUEST
    return isinstance(error, ModelUnavailable) and error.status == SERVER_ERROR


def _generation_config(
    system: str | None, *, mime_type: str | None = None, schema: dict[str, Any] | None = None
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=TEMPERATURE,
        system_instruction=system,
        response_mime_type=mime_type,
        response_schema=copy.deepcopy(schema) if schema is not None else None,
    )


def _raise_if_refused(response: types.GenerateContentResponse) -> None:
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        raise ModelRefused(f"Gemini blocked the request ({_enum_text(feedback.block_reason)}).")
    reason = _finish_reason(response)
    if reason in _REFUSAL_FINISH_REASONS:
        raise ModelRefused(f"Gemini stopped the answer ({reason}).")


def _finish_reason(response: types.GenerateContentResponse) -> str | None:
    candidates = response.candidates or []
    if not candidates or candidates[0].finish_reason is None:
        return None
    return _enum_text(candidates[0].finish_reason)


def _enum_text(value: Any) -> str:
    return str(getattr(value, "value", value))


def _tokens(usage: types.GenerateContentResponseUsageMetadata | None, field: str) -> int:
    return int(getattr(usage, field, None) or 0) if usage is not None else 0
