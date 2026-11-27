from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any

from app.adapters.demo_answers import DEMO_OUTCOMES, BilledLine, DemoCodeBook, DemoOutcome, DemoRequest, demo_bundle
from app.ai.contracts import ModelReply
from app.ai.errors import ModelRequestRejected
from app.ai.prompts.context import ADDENDUM_HEADING_PATTERN, CONTEXT_HEADING

__all__ = ["DEMO_MODEL", "DemoModelClient", "demo_outcome", "read_request"]

DEMO_MODEL = "bodha-demo"
_NOTE = re.compile(r"<clinical_note>\n(?P<text>.*)\n</clinical_note>", re.S)


class DemoModelClient:
    def __init__(self, codes: DemoCodeBook) -> None:
        self._codes = codes

    async def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None,
        pdf: bytes | None = None,
        system: str | None = None,
    ) -> ModelReply:
        if schema is None:
            raise ModelRequestRejected("The demo model answers schema-bound review calls only.")
        parts = tuple(schema.get("properties", {}))
        bundle = demo_bundle(parts, read_request(prompt, pdf), self._codes)
        return ModelReply(text=json.dumps(bundle), model=DEMO_MODEL, input_tokens=0, output_tokens=0)


def demo_outcome(document: bytes) -> DemoOutcome:
    return DEMO_OUTCOMES[hashlib.sha256(document).digest()[0] % len(DEMO_OUTCOMES)]


def read_request(prompt: str, pdf: bytes | None) -> DemoRequest:
    context = _encounter(prompt)
    found = _NOTE.search(prompt)
    text = found["text"] if found else ""
    document, *addenda = ADDENDUM_HEADING_PATTERN.split(text, maxsplit=1)
    outcome: DemoOutcome = "matches" if addenda else demo_outcome(document.encode() if document.strip() else pdf or b"")
    billed = tuple(BilledLine(item["code"], item["type"]) for item in context["billedCodes"])
    return DemoRequest(outcome, text, billed, date.fromisoformat(context["dateOfService"]))


def _encounter(prompt: str) -> dict[str, Any]:
    heading = prompt.find(CONTEXT_HEADING)
    start = prompt.find("{", heading) if heading >= 0 else -1
    if start < 0:
        raise ModelRequestRejected("The demo model found no encounter context in the prompt.")
    try:
        context, _ = json.JSONDecoder().raw_decode(prompt, start)
    except json.JSONDecodeError as error:
        raise ModelRequestRejected("The demo model could not read the encounter context.") from error
    return context
