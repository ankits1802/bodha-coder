from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.db import SessionFactory
from app.main import app
from app.services.ehr_pull import poll_ehr_connections, pull_practice
from tests.builders import Harness, Practice, practice_with_provider
from tests.ehr_fakes import BASE, FakeEhr, document, encounter, practitioner
from tests.fakes import text_pdf

API = "/api/practice/ehr-connection"
CHICAGO = ZoneInfo("America/Chicago")
NOW = datetime.now(UTC).replace(microsecond=0)
TODAY = NOW.astimezone(CHICAGO).date()
START = TODAY - timedelta(days=5)
SEEN = TODAY - timedelta(days=2)
SCOPES = ["system/DocumentReference.read", "system/Encounter.read", "system/Practitioner.read", "system/Binary.read"]
NOTE_PDF = text_pdf("Progress note. Elena Varga MD. Follow-up of diabetes, stable on metformin.")
OTHER_PDF = text_pdf("Progress note. Elena Varga MD. Hypertension follow-up, blood pressure at goal.")
PROVIDER_NPI = "1234567893"


def settings_body(**changes: Any) -> dict[str, Any]:
    return {
        "base_url": BASE,
        "client_id": "bodha-lakeside",
        "scopes": SCOPES,
        "note_types": ["progress"],
        "start_date": START.isoformat(),
        **changes,
    }


async def connected(harness: Harness, *, algorithm: str = "RS384", **changes: Any) -> Practice:
    practice = await practice_with_provider(harness)
    key = await harness.client.post(f"{API}/key", headers=practice.admin, json={"algorithm": algorithm})
    assert key.status_code == 200, key.text
    saved = await harness.client.put(API, headers=practice.admin, json=settings_body(**changes))
    assert saved.status_code == 200, saved.text
    return practice


def visit(ehr: FakeEhr, *, start: str | None = None, class_code: str = "AMB", npi: str = PROVIDER_NPI) -> None:
    ehr.resources["Encounter/e1"] = encounter(
        "e1", start or f"{SEEN.isoformat()}T09:30:00-06:00", class_code=class_code
    )
    ehr.resources["Practitioner/p1"] = practitioner("p1", npi)


def one_note(ehr: FakeEhr, **changes: Any) -> None:
    visit(ehr)
    ehr.binaries["Binary/b1"] = (NOTE_PDF, "application/pdf")
    ehr.documents.append(document("d1", **changes))


async def poll(harness: Harness, now: datetime = NOW) -> int:
    async with SessionFactory() as db:
        return await poll_ehr_connections(db, harness.store, app.state.outbound, now)


async def pull_again(harness: Harness, practice: Practice, now: datetime) -> int:
    async with SessionFactory() as db:
        return await pull_practice(db, harness.store, app.state.outbound, practice.id, now)


async def documents(harness: Harness, practice: Practice) -> list[dict[str, Any]]:
    response = await harness.client.get(f"{API}/documents", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def runs(harness: Harness, practice: Practice) -> list[dict[str, Any]]:
    response = await harness.client.get(f"{API}/runs", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()["items"]
