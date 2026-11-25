from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.audit import stamp_audit_ids
from app.ai.bundle import bundle_schema, validated_parts
from app.ai.cdi import stamp_cdi_ids
from app.ai.contracts import (
    CodeReview,
    ModelClient,
    ModelReply,
    PatientFacts,
    ReviewInputs,
    ReviewOutcome,
    ReviewReport,
    Section,
)
from app.ai.errors import ModelError
from app.ai.json_text import parse_json_loose
from app.ai.mips import MipsReview, empty_mips, scope_allows_nothing, scoped_mips
from app.ai.parts import SECTION_ORDER, TOP_UP_OPTIONAL, Part, in_part_order
from app.ai.prompts.context import SYSTEM_INSTRUCTION, note_text_to_review
from app.ai.prompts.frame import render_review_prompt

__all__ = ["PROMPT_VERSION", "review_note"]

PROMPT_VERSION = "2026.11.1"

logger = logging.getLogger(__name__)


async def review_note(client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
    _check_inputs(inputs)
    parts = _model_parts(inputs)
    replies: list[ModelReply] = []
    valid: dict[Part, Any] = {}
    if parts:
        first = await _ask(client, inputs, parts)
        replies.append(first)
        valid = _parsed_parts(first, parts, inputs)
        missing = tuple(part for part in parts if part not in valid)
        if any(part not in TOP_UP_OPTIONAL for part in missing):
            recovered, top_up = await _top_up(client, inputs, missing)
            valid |= recovered
            replies.extend(top_up)
    return ReviewOutcome(
        report=_report(valid, inputs),
        prompt_version=PROMPT_VERSION,
        replies=tuple(replies),
        failed_sections=_failed_sections(parts, valid),
    )


def _check_inputs(inputs: ReviewInputs) -> None:
    if not inputs.sections:
        raise ValueError("ReviewInputs.sections is empty: request at least one section.")
    unknown = sorted(set(inputs.sections) - set(SECTION_ORDER))
    if unknown:
        raise ValueError(f"ReviewInputs.sections names unknown sections: {', '.join(unknown)}.")
    if note_text_to_review(inputs) is None and not inputs.pdf:
        raise ValueError("ReviewInputs has neither note text nor a PDF to review.")


def _model_parts(inputs: ReviewInputs) -> tuple[Part, ...]:
    parts: set[Part] = set(inputs.sections)
    if not inputs.billed_codes:
        parts.discard("code_review")
    if scope_allows_nothing(inputs.mips_scope):
        parts.discard("mips")
    if _pdf_for(inputs) is not None:
        parts.add("extracted_text")
    if parts:
        parts.add("patient")
    return in_part_order(parts)


def _pdf_for(inputs: ReviewInputs) -> bytes | None:
    return inputs.pdf if note_text_to_review(inputs) is None else None


async def _ask(client: ModelClient, inputs: ReviewInputs, parts: Sequence[Part]) -> ModelReply:
    return await client.generate(
        render_review_prompt(inputs, parts),
        schema=bundle_schema(parts),
        pdf=_pdf_for(inputs),
        system=SYSTEM_INSTRUCTION,
    )


async def _top_up(
    client: ModelClient, inputs: ReviewInputs, missing: Sequence[Part]
) -> tuple[dict[Part, Any], tuple[ModelReply, ...]]:
    logger.info("review top-up for %s", ", ".join(missing))
    try:
        reply = await _ask(client, inputs, missing)
    except ModelError as error:
        logger.warning("review top-up for %s failed (%s)", ", ".join(missing), type(error).__name__)
        return {}, ()
    return _parsed_parts(reply, missing, inputs), (reply,)


def _parsed_parts(reply: ModelReply, parts: Sequence[Part], inputs: ReviewInputs) -> dict[Part, Any]:
    try:
        payload = parse_json_loose(reply.text)
    except ValueError:
        logger.warning("model answer is not parseable JSON (%d characters); every part failed", len(reply.text))
        return {}
    return validated_parts(payload, parts, inputs.billed_codes)


def _report(valid: Mapping[Part, Any], inputs: ReviewInputs) -> ReviewReport:
    return ReviewReport(
        patient=valid.get("patient") or PatientFacts(),
        extracted_text=valid.get("extracted_text"),
        em=valid.get("em"),
        diagnoses=valid.get("diagnoses"),
        code_review=_code_review(valid, inputs),
        cdi=stamp_cdi_ids(valid["cdi"]) if "cdi" in valid else None,
        audit=stamp_audit_ids(valid["audit"]) if "audit" in valid else None,
        mips=_mips(valid, inputs),
    )


def _code_review(valid: Mapping[Part, Any], inputs: ReviewInputs) -> CodeReview | None:
    if "code_review" in inputs.sections and not inputs.billed_codes:
        return CodeReview()
    return valid.get("code_review")


def _mips(valid: Mapping[Part, Any], inputs: ReviewInputs) -> MipsReview | None:
    if "mips" not in inputs.sections:
        return None
    if scope_allows_nothing(inputs.mips_scope):
        return empty_mips(inputs.mips_scope)
    if "mips" not in valid:
        return None
    return scoped_mips(valid["mips"], inputs.mips_scope)


def _failed_sections(parts: Sequence[Part], valid: Mapping[Part, Any]) -> frozenset[Section]:
    return frozenset(section for section in SECTION_ORDER if section in parts and section not in valid)
