from __future__ import annotations

import json
from dataclasses import dataclass

import pyotp
from httpx import AsyncClient

from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.security import hash_password
from app.models import User
from app.services.analysis import AnalysisDeps
from app.worker import process_one
from tests.fakes import NOTE_TEXT, FakeMessenger, FakeStore, ScriptedReviewer, text_pdf

FILE_NAME = "2026-11-25 - REYES MARISOL - 99215 - Progress.pdf"
BILLED = "99215, I10, E11.9, N18.30"
PASSWORD = "correct-horse-staple"


@dataclass
class Harness:
    client: AsyncClient
    store: FakeStore
    messenger: FakeMessenger


async def sign_in(client: AsyncClient, email: str, *, secret_box: dict[str, str] | None = None) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    if "mfa" in body:
        box = secret_box if secret_box is not None else {}
        if body["mfa"] == "setup":
            setup = await client.post("/api/auth/mfa/setup", json={"mfa_token": body["mfa_token"]})
            box[email] = setup.json()["secret"]
        code = pyotp.TOTP(box[email]).now()
        body = (await client.post("/api/auth/mfa/verify", json={"mfa_token": body["mfa_token"], "code": code})).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


async def create_hq_user(email: str = "hq@bodha.example.com") -> None:
    async with SessionFactory() as db:
        db.add(User(email=email, name="Bodha Admin", role="hq", status="active", password_hash=hash_password(PASSWORD)))
        await db.commit()


async def accept_invite(harness: Harness) -> None:
    token = harness.messenger.last_fragment()
    response = await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    assert response.status_code == 204, response.text


async def new_practice(harness: Harness, *, name: str, admin_email: str, hq_headers: dict[str, str]) -> str:
    response = await harness.client.post(
        "/api/hq/practices",
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


async def read_next_note(harness: Harness, icd_catalog, report: ReviewReport | None = None) -> ScriptedReviewer:
    reviewer = ScriptedReviewer(report or marisol_report())
    deps = AnalysisDeps(reviewer, None, harness.store, icd_catalog)
    assert await process_one(deps, get_settings()) is True
    return reviewer


async def reviewed_note(harness: Harness, icd_catalog) -> tuple[Practice, str]:
    practice = await practice_with_provider(harness)
    upload = await upload_note(harness, practice)
    assert upload.status_code == 200, upload.text
    await read_next_note(harness, icd_catalog)
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    return practice, listing.json()["items"][0]["id"]
