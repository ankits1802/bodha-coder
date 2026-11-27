from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.adapters.billing_contract import (
    BillingUnavailable,
    CheckoutRequest,
    ProcessorEvent,
    ProcessorSubscription,
    SubscriptionRef,
    WebhookRefused,
)
from app.adapters.oidc import ProviderIdentity
from app.adapters.oidc_providers import IdentityRefused, provider_label
from app.ai.contracts import ModelClient, ModelReply, ModelRequest, ReviewInputs, ReviewOutcome, ReviewReport

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

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def signed_url(self, key: str, *, seconds: int) -> str:
        return f"https://storage.test/{key}?expires={seconds}"

    async def delete(self, keys: list[str]) -> None:
        for key in keys:
            self.objects.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        if not prefix.endswith("/") or prefix == "/":
            raise ValueError(f"refusing to delete under {prefix!r}")
        doomed = [key for key in self.objects if key.startswith(prefix)]
        await self.delete(doomed)
        return len(doomed)


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


@dataclass(frozen=True)
class ProviderExchange:
    code: str
    verifier: str
    nonce: str
    redirect_uri: str


@dataclass
class FakeProvider:
    name: str = "google"
    enabled: bool = True
    identities: dict[str, ProviderIdentity] = field(default_factory=dict)
    refusals: dict[str, IdentityRefused] = field(default_factory=dict)
    exchanges: list[ProviderExchange] = field(default_factory=list)
    redirects: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return provider_label(self.name)

    async def authorization_url(self, *, state: str, nonce: str, verifier: str, redirect_uri: str) -> str:
        self.redirects.append(redirect_uri)
        return f"https://accounts.example.com/{self.name}/auth?state={state}"

    async def identity(self, code: str, *, verifier: str, nonce: str, redirect_uri: str) -> ProviderIdentity:
        self.exchanges.append(ProviderExchange(code, verifier, nonce, redirect_uri))
        if code in self.refusals:
            raise self.refusals[code]
        if code not in self.identities:
            raise IdentityRefused(f"{self.label} did not accept the sign-in")
        return self.identities[code]

    def returns(self, code: str, *, subject: str, email: str, name: str = "") -> None:
        self.identities[code] = ProviderIdentity(self.name, subject, email, name)


@dataclass
class FakeBillingProvider:
    name: str
    checkouts: list[CheckoutRequest] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)
    quantities: list[tuple[str, int]] = field(default_factory=list)
    subscriptions: dict[str, ProcessorSubscription] = field(default_factory=dict)
    unavailable: bool = False

    async def checkout_url(self, request: CheckoutRequest) -> str:
        self.checkouts.append(request)
        return f"https://pay.example.com/{self.name}/checkout"

    async def manage_url(self, ref: SubscriptionRef, *, return_url: str) -> str:
        return f"https://pay.example.com/{self.name}/manage/{ref.subscription_id}"

    async def cancel_at_period_end(self, ref: SubscriptionRef) -> None:
        self.cancelled.append(ref.subscription_id)

    async def set_quantity(self, ref: SubscriptionRef, quantity: int) -> None:
        if self.unavailable:
            raise BillingUnavailable()
        self.quantities.append((ref.subscription_id, quantity))

    async def read_event(self, body: bytes, headers: Mapping[str, str]) -> ProcessorEvent:
        if headers.get("x-test-signature") != "valid":
            raise WebhookRefused()
        sent = json.loads(body)
        return ProcessorEvent(sent["id"], sent["type"], sent.get("subscription"), sent.get("payment"))

    async def subscription(self, subscription_id: str) -> ProcessorSubscription:
        return self.subscriptions[subscription_id]


@dataclass
class ScriptedReviewer:
    report: ReviewReport
    calls: list[ReviewInputs] = field(default_factory=list)
    requests: tuple[ModelRequest, ...] = ()
    replies: tuple[ModelReply, ...] = ()

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        self.calls.append(inputs)
        return ReviewOutcome(report=self.report, prompt_version="test", replies=self.replies, requests=self.requests)


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
