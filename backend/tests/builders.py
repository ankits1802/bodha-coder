from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import pyotp
from httpx import AsyncClient
from sqlalchemy import update

from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.model_prices import PriceBook
from app.core.security import hash_password
from app.models import User
from app.services.analysis import AnalysisDeps, Reviewer
from app.worker import process_one
from tests.fakes import (
    NOTE_TEXT,
    FakeBillingProvider,
    FakeImageModel,
    FakeMessenger,
    FakeProvider,
    FakeStore,
    ScriptedReviewer,
    signature_data_url,
    text_pdf,
)

FILE_NAME = "2026-11-25 - REYES MARISOL - 99215 - Progress.pdf"
BILLED = "99215, I10, E11.9, N18.30"
PASSWORD = "correct-horse-staple"
DOCUMENTED = {"reason": "documentation", "note": None}
ADMIN_SITE = "https://admin.test"


@dataclass
class Harness:
    client: AsyncClient
    store: FakeStore
    messenger: FakeMessenger
    providers: dict[str, FakeProvider]
    billing: dict[str, FakeBillingProvider]
    image_model: FakeImageModel

    @property
    def google(self) -> FakeProvider:
        return self.providers["google"]


async def sign_in(
    client: AsyncClient, email: str, *, secret_box: dict[str, str] | None = None, site: str = ""
) -> dict[str, str]:
    response = await client.post(f"{site}/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    if "mfa" in body:
        box = secret_box if secret_box is not None else {}
        if body["mfa"] == "setup":
            setup = await client.post(f"{site}/api/auth/mfa/setup", json={"mfa_token": body["mfa_token"]})
            box[email] = setup.json()["secret"]
        body = await pass_two_step(client, email, body["mfa_token"], box[email], site=site)
    return {"Authorization": f"Bearer {body['access_token']}"}


async def adopt_signature(client: AsyncClient, headers: dict[str, str], *, name: str = "Practice Admin") -> str:
    body = {"source": "typed", "typed_name": name, "image": signature_data_url()}
    drafted = await client.post("/api/signature/drafts", headers=headers, json=body)
    assert drafted.status_code == 200, drafted.text
    signature_id = drafted.json()["id"]
    adopted = await client.post(f"/api/signature/drafts/{signature_id}/adopt", headers=headers)
    assert adopted.status_code == 200, adopted.text
    return signature_id


async def pass_two_step(client: AsyncClient, email: str, mfa_token: str, secret: str, *, site: str = "") -> dict:
    await forget_last_code(email)
    code = pyotp.TOTP(secret).now()
    response = await client.post(f"{site}/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert response.status_code == 200, response.text
    return response.json()


async def forget_last_code(email: str) -> None:
    async with SessionFactory() as db:
        await db.execute(update(User).where(User.email == email).values(mfa_last_step=None))
        await db.commit()


async def create_hq_user(email: str = "hq@bodha.example.com") -> None:
    async with SessionFactory() as db:
        db.add(User(email=email, name="Bodha Admin", role="hq", status="active", password_hash=hash_password(PASSWORD)))
        await db.commit()


async def accept_invite(harness: Harness, *, site: str = "") -> None:
    token = harness.messenger.last_fragment()
    response = await harness.client.post(f"{site}/api/auth/password", json={"token": token, "password": PASSWORD})
    assert response.status_code == 204, response.text


async def new_practice(
    harness: Harness, *, name: str, admin_email: str, hq_headers: dict[str, str], hq_site: str = ""
) -> str:
    response = await harness.client.post(
        f"{hq_site}/api/hq/practices",
        headers=hq_headers,
        json={
            "name": name,
            "admin_name": "Practice Admin",
            "admin_email": admin_email,
            "plan": "professional",
            "seats": 10,
        },
    )
    assert response.status_code == 200, response.text
    await accept_invite(harness)
    return response.json()["id"]


def marisol_report() -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(name="Marisol Reyes", age=67, sex="female"),
        em=EmReview(
            code="99214",
            mdm_level="Moderate",
            justification="Moderate decision-making.",
            evidence=["increase metformin"],
        ),
        diagnoses=[
            DiagnosisFinding(
                name="Type 2 diabetes with hyperglycemia", icd10="E11.65", status="supported", evidence=["A1c 8.4"]
            ),
            DiagnosisFinding(
                name="Hypertensive CKD", icd10="I12.9", status="supported", evidence=["Hypertension above goal"]
            ),
            DiagnosisFinding(
                name="CKD, stable",
                icd10="N18.30",
                status="needs_specificity",
                evidence=["CKD, stable"],
                suggestion="Stage not documented",
            ),
            DiagnosisFinding(
                name="Tingling in both feet", icd10="R20.2", status="supported", evidence=["tingling in both feet"]
            ),
        ],
    )


@dataclass
class Practice:
    id: str
    admin: dict[str, str]
    provider_id: str
    secrets: dict[str, str]


async def practice_with_provider(
    harness: Harness, *, name: str = "Lakeside", admin_email: str = "admin@lakeside.example.com"
) -> Practice:
    secrets: dict[str, str] = {}
    await create_hq_user(f"hq-{admin_email}")
    hq = await sign_in(harness.client, f"hq-{admin_email}", secret_box=secrets)
    practice_id = await new_practice(harness, name=name, admin_email=admin_email, hq_headers=hq)
    admin = await sign_in(harness.client, admin_email, secret_box=secrets)
    await adopt_signature(harness.client, admin)
    provider = await harness.client.post(
        "/api/providers",
        headers=admin,
        json={
            "name": "Elena Varga",
            "credential": "MD",
            "specialty": "Internal medicine",
            "npi": "1234567893",
            "place_code": "11",
            "email": "varga@clinic.example.com",
        },
    )
    assert provider.status_code == 200, provider.text
    return Practice(practice_id, admin, provider.json()["id"], secrets)


async def practice_with_member(harness: Harness, *, name: str, email: str, role: str) -> Practice:
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name=name, email=email, role=role)
    return practice


async def invite_member(harness: Harness, practice: Practice, *, name: str, email: str, role: str) -> str:
    invited = await harness.client.post(
        "/api/team", headers=practice.admin, json={"name": name, "email": email, "role": role}
    )
    assert invited.status_code == 200, invited.text
    await accept_invite(harness)
    return invited.json()["id"]


async def back_from_google(harness: Harness, code: str):
    return await back_from(harness, "google", code)


async def back_from(harness: Harness, provider: str, code: str, *, site: str = ""):
    start = await harness.client.get(f"{site}/api/auth/{provider}/start")
    assert start.status_code == 302, start.text
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    return await harness.client.get(f"{site}/api/auth/{provider}/callback", params={"code": code, "state": state})


def sign_in_page(fragment: str) -> str:
    return f"{get_settings().app_url}/sign-in#{fragment}"


async def upload_note(harness: Harness, practice: Practice, *, file_name: str = FILE_NAME, body: str = NOTE_TEXT):
    return await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": "2026-11-25",
            "place_code": "11",
            "visit_type": "Established patient",
            "details": json.dumps([{"billed": BILLED}]),
        },
        files=[("files", (file_name, text_pdf(body), "application/pdf"))],
    )


def analysis_deps(
    harness: Harness, icd_catalog, reviewer: Reviewer, *, prices: PriceBook | None = None
) -> AnalysisDeps:
    book = prices if prices is not None else PriceBook(get_settings().model_prices)
    return AnalysisDeps(reviewer, None, harness.store, icd_catalog, book)


async def read_next_note(harness: Harness, icd_catalog, report: ReviewReport | None = None) -> ScriptedReviewer:
    reviewer = ScriptedReviewer(report or marisol_report())
    deps = analysis_deps(harness, icd_catalog, reviewer)
    assert await process_one(deps, get_settings()) is True
    return reviewer


async def reviewed_note(harness: Harness, icd_catalog) -> tuple[Practice, str]:
    practice = await practice_with_provider(harness)
    upload = await upload_note(harness, practice)
    assert upload.status_code == 200, upload.text
    await read_next_note(harness, icd_catalog)
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    return practice, listing.json()["items"][0]["id"]
