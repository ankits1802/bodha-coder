from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from app.ai.contracts import ReviewInputs
from app.ai.parts import Part
from app.ai.prompts.audit import AUDIT_TASK
from app.ai.prompts.cdi import CDI_TASK
from app.ai.prompts.code_review import CODE_REVIEW_TASK
from app.ai.prompts.context import note_text_to_review, render_context, render_note
from app.ai.prompts.diagnoses import DIAGNOSES_TASK
from app.ai.prompts.em import EM_TASK
from app.ai.prompts.hcc import HCC_TASK
from app.ai.prompts.mips import render_mips_task
from app.ai.prompts.patient import EXTRACTED_TEXT_TASK, PATIENT_TASK

__all__ = ["render_review_prompt"]

_COUNT_WORDS = ("NO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")

_HEAD = """
You are a medical coding engine reviewing ONE clinical note for a certified coder. You will perform {count} separate
task(s) over this note and return every answer in a single JSON object. Each task's instructions are given below.
Follow each one exactly as if it were the only task you had been given: do not let one task's conclusions relax
another's rules, and do not skip a task because another one already mentioned the same diagnosis.

Every quote you return as evidence is copied verbatim from the note, at most 200 characters, never paraphrased.
"""

_TASK_HEADER = """
# ============================================================
# TASK "{name}": {title}
# ============================================================
"""

_OUTPUT_FORMAT = """
# ============================================================
# COMBINED OUTPUT FORMAT
# ============================================================

Return ONE JSON object with EXACTLY these {count} top-level key(s) and nothing else:
{keys}

Do NOT merge the answers. Do NOT rename, nest or omit these keys. Do NOT wrap the result in any other key. Each
value keeps the exact field names its own task describes.
"""

_TITLES: Mapping[Part, str] = MappingProxyType(
    {
        "patient": "PATIENT FACTS",
        "extracted_text": "PDF TEXT",
        "em": "E/M CODE",
        "diagnoses": "ICD-10-CM DIAGNOSES",
        "code_review": "BILLED CODE REVIEW",
        "cdi": "CDI GAP SCAN",
        "audit": "DOCUMENTATION AUDIT",
        "mips": "MIPS QUALITY MEASURES",
        "hcc": "RISK ADJUSTMENT: SUSPECTED CONDITIONS",
    }
)

_FIXED_TASKS: Mapping[Part, str] = MappingProxyType(
    {
        "patient": PATIENT_TASK,
        "extracted_text": EXTRACTED_TEXT_TASK,
        "em": EM_TASK,
        "diagnoses": DIAGNOSES_TASK,
        "code_review": CODE_REVIEW_TASK,
        "cdi": CDI_TASK,
        "audit": AUDIT_TASK,
        "hcc": HCC_TASK,
    }
)

_SHAPES: Mapping[Part, str] = MappingProxyType(
    {
        "extracted_text": '"... the text TASK "extracted_text" specifies ..."',
        "diagnoses": '[ ... the array TASK "diagnoses" specifies ... ]',
    }
)


def render_review_prompt(inputs: ReviewInputs, parts: Sequence[Part]) -> str:
    if not parts:
        raise ValueError("a review prompt needs at least one part")
    count = _COUNT_WORDS[len(parts)]
    tasks = "".join(_task_block(part, inputs) for part in parts)
    return (
        _HEAD.replace("{count}", count)
        + render_context(inputs)
        + render_note(note_text_to_review(inputs), with_pdf=bool(inputs.pdf))
        + tasks
        + _output_format(parts, count)
    )


def _task_block(part: Part, inputs: ReviewInputs) -> str:
    header = _TASK_HEADER.replace("{name}", part).replace("{title}", _TITLES[part])
    text = render_mips_task(inputs.mips_scope) if part == "mips" else _FIXED_TASKS[part]
    return header + text


def _output_format(parts: Sequence[Part], count: str) -> str:
    keys = ",\n".join(f'  "{part}": {_shape(part)}' for part in parts)
    return _OUTPUT_FORMAT.replace("{count}", count).replace("{keys}", "{\n" + keys + "\n}")


def _shape(part: Part) -> str:
    return _SHAPES.get(part, f'{{ ... the object TASK "{part}" specifies ... }}')
