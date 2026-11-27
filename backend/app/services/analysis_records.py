from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import timedelta
from itertools import zip_longest
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, analysis_prompt_key
from app.ai.contracts import BilledCode, ModelReply, ModelRequest, ReviewOutcome
from app.codes.billing_codes import Code
from app.core.config import get_settings
from app.models import Analysis, AnalysisFailure, Note

__all__ = [
    "PROMPT_RECORD_VERSION",
    "billed_context",
    "generation_settings",
    "keep_run_inputs",
    "prompt_record",
    "record_failure",
    "sha256_of_json",
]

PROMPT_RECORD_VERSION = 1
JSON_TYPE = "application/json"


def billed_context(codes: Sequence[Code | BilledCode]) -> list[dict[str, Any]]:
    return [
        {"code": code.code, "type": code.type, "modifiers": list(code.modifiers), "units": code.units} for code in codes
    ]


def sha256_of_json(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prompt_record(outcome: ReviewOutcome, *, document_key: str | None, document_sha256: str | None) -> dict[str, Any]:
    return {
        "version": PROMPT_RECORD_VERSION,
        "prompt_version": outcome.prompt_version,
        "document": {"key": document_key, "sha256": document_sha256},
        "requests": [
            {**_request_view(request), **_reply_settings(reply)}
            for request, reply in zip_longest(outcome.requests, outcome.replies)
        ],
    }


def generation_settings(outcome: ReviewOutcome) -> dict[str, Any]:
    return {
        "calls": [
            {
                "model": reply.model if reply else None,
                "schema_sha256": sha256_of_json(request.schema) if request and request.schema is not None else None,
                **_reply_settings(reply),
            }
            for request, reply in zip_longest(outcome.requests, outcome.replies)
        ]
    }


async def keep_run_inputs(store: ObjectStore, analysis: Analysis, note: Note, outcome: ReviewOutcome) -> None:
    sent = bool(outcome.requests)
    document_key = note.file_key if sent else None
    record = prompt_record(outcome, document_key=document_key, document_sha256=note.file_sha256 if sent else None)
    data = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    key = analysis_prompt_key(note.practice_id, note.id, analysis.revision)
    await store.put(key, data, content_type=JSON_TYPE)
    analysis.prompt_key, analysis.prompt_sha256 = key, hashlib.sha256(data).hexdigest()
    analysis.app_version = get_settings().app_version
    analysis.generation = generation_settings(outcome)
    analysis.document_key = document_key


def record_failure(db: AsyncSession, analysis: Analysis, error: str, *, retry_in: timedelta | None) -> None:
    db.add(
        AnalysisFailure(
            analysis_id=analysis.id, attempt=analysis.attempts, error=error[:300], retried=retry_in is not None
        )
    )


def _request_view(request: ModelRequest | None) -> dict[str, Any]:
    if request is None:
        return {"system": None, "prompt": None, "schema": None}
    return {"system": request.system, "prompt": request.prompt, "schema": request.schema}


def _reply_settings(reply: ModelReply | None) -> dict[str, Any]:
    if reply is None:
        return {"temperature": None, "schema_applied": None}
    return {"temperature": reply.temperature, "schema_applied": reply.schema_applied}
