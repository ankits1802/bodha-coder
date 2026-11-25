from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Annotated, Any

from pydantic import AfterValidator, TypeAdapter, ValidationError, create_model

from app.ai.audit import AuditChecklistOutput
from app.ai.cdi import CDIGapScanOutput
from app.ai.contracts import BilledCode, CodeReview, DiagnosisFinding, EmReview, PatientFacts
from app.ai.hcc import HccScanOutput
from app.ai.mips import MIPSQualityMeasuresOutput
from app.ai.parts import Part
from app.ai.schema import gemini_schema

__all__ = ["bundle_schema", "validated_parts"]

logger = logging.getLogger(__name__)


def _non_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("the text is blank")
    return text


def _coded(review: EmReview) -> EmReview:
    if not review.code.strip():
        raise ValueError("the E/M answer names no code")
    return review


_PART_TYPES: Mapping[Part, Any] = MappingProxyType(
    {
        "patient": PatientFacts,
        "extracted_text": Annotated[str, AfterValidator(_non_blank)],
        "em": Annotated[EmReview, AfterValidator(_coded)],
        "diagnoses": list[DiagnosisFinding],
        "code_review": CodeReview,
        "cdi": CDIGapScanOutput,
        "audit": AuditChecklistOutput,
        "mips": MIPSQualityMeasuresOutput,
        "hcc": HccScanOutput,
    }
)

_ADAPTERS: Mapping[Part, TypeAdapter[Any]] = MappingProxyType(
    {part: TypeAdapter(kind) for part, kind in _PART_TYPES.items()}
)


def bundle_schema(parts: Iterable[Part]) -> dict[str, Any]:
    fields: dict[str, Any] = {part: (_PART_TYPES[part] | None, None) for part in parts}
    return gemini_schema(create_model("ReviewBundle", **fields))


def validated_parts(payload: object, parts: Iterable[Part], billed: Sequence[BilledCode]) -> dict[Part, Any]:
    if not isinstance(payload, dict):
        logger.warning("model answer is a JSON %s, not an object; every part failed", type(payload).__name__)
        return {}
    valid: dict[Part, Any] = {}
    for part in parts:
        value = _validated(part, payload.get(part))
        if part == "code_review" and value is not None:
            value = _covering_billed(value, billed)
        if value is not None:
            valid[part] = value
    return valid


def _validated(part: Part, raw: object) -> Any:
    if raw is None:
        logger.warning("model answer has no %s", part)
        return None
    try:
        return _ADAPTERS[part].validate_python(raw)
    except ValidationError as error:
        logger.warning("model answer's %s is invalid (%d errors)", part, error.error_count())
        return None


def _covering_billed(review: CodeReview, billed: Sequence[BilledCode]) -> CodeReview | None:
    by_code = {_code_key(item.code): item for item in review.items}
    wanted = {_code_key(code.code): code.code for code in billed}
    missing = [key for key in wanted if key not in by_code]
    if missing:
        logger.warning("model answer's code_review misses %d of %d billed codes", len(missing), len(wanted))
        return None
    items = [by_code[key].model_copy(update={"code": code}) for key, code in wanted.items()]
    return review.model_copy(update={"items": items})


def _code_key(code: str) -> str:
    return code.strip().upper()
