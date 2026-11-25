from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.contracts import ModelClient, ModelReply, ReviewInputs, ReviewOutcome, ReviewReport

NOTE_TEXT = (
    "Follow-up of diabetes and blood pressure. 67-year-old woman with type 2 diabetes, hypertension and chronic kidney "
    "disease. A1c 8.4. eGFR 38. Assessment and plan: Type 2 diabetes with hyperglycemia, increase metformin. "
    "Hypertension above goal, add amlodipine. CKD, stable. Occasional tingling in both feet."
)


@dataclass(frozen=True)
class SentCall:
    prompt: str
    schema: dict[str, Any] | None
    pdf: bytes | None
    system: str | None

    def requested_parts(self) -> set[str]:
        return set((self.schema or {}).get("properties", {}))


@dataclass
class FakeModelClient:
    answers: list[str]
    calls: list[SentCall] = field(default_factory=list)

    async def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None,
        pdf: bytes | None = None,
        system: str | None = None,
    ) -> ModelReply:
        self.calls.append(SentCall(prompt, schema, pdf, system))
        if not self.answers:
            raise AssertionError("the fake model has no scripted answer left")
        return ModelReply(text=self.answers.pop(0), model="fake-gemini", input_tokens=100, output_tokens=50)


class FakeStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self.objects[key] = data

    async def get(self, key: str) -> bytes:
        return self.objects[key]

    async def signed_url(self, key: str, *, seconds: int) -> str:
        return f"https://storage.test/{key}?expires={seconds}"

    async def delete(self, keys: list[str]) -> None:
        for key in keys:
            self.objects.pop(key, None)


@dataclass
class FakeMessenger:
    sent: list[tuple[str, str]] = field(default_factory=list)

    async def email(self, to: str, *, subject: str, body: str) -> None:
        self.sent.append((to, body))

    async def sms(self, to: str, *, body: str) -> None:
        self.sent.append((to, body))

    def last_fragment(self) -> str:
        found = re.search(r"#([A-Za-z0-9_-]+)", self.sent[-1][1])
        assert found, "no link in the last message"
        return found.group(1)

    def last_code(self) -> str:
        found = re.search(r"\b(\d{6})\b", self.sent[-1][1])
        assert found, "no code in the last message"
        return found.group(1)


@dataclass
class ScriptedReviewer:
    report: ReviewReport
    calls: list[ReviewInputs] = field(default_factory=list)

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        self.calls.append(inputs)
        return ReviewOutcome(report=self.report, prompt_version="test")


def text_pdf(text: str) -> bytes:
    stream = f"BT /F1 10 Tf 40 760 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body, offsets = b"%PDF-1.4\n", []
    for number, content in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n".encode() + content + b"\nendobj\n"
    xref = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    body += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return body


@dataclass
class FailingReviewer:
    error: Exception

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        raise self.error
