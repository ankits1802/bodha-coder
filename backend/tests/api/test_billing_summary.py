from datetime import timedelta

from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import AddendumRequest, utcnow
from app.services.billing import safe_cell
from app.services.reminders import expire_requests
from tests.builders import reviewed_note


async def _summary(harness, practice) -> dict[str, int]:
    return (await harness.client.get("/api/billing", headers=practice.admin)).json()["summary"]


async def test_billing_counts_ready_held_and_exported_today(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage?"}], "channel": "email", "hold": True},
    )
    assert await _summary(harness, practice) == {"ready": 0, "exported_today": 0, "held_for_provider": 1}

    async with SessionFactory() as db:
        await db.execute(update(AddendumRequest).values(expires_at=utcnow() - timedelta(minutes=1)))
        await db.commit()
        await expire_requests(db)
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert await _summary(harness, practice) == {"ready": 1, "exported_today": 0, "held_for_provider": 0}

    await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    assert await _summary(harness, practice) == {"ready": 0, "exported_today": 1, "held_for_provider": 0}


async def test_an_export_can_be_downloaded_again_without_changing_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    first = await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    exported = (await harness.client.get("/api/billing?show=exported", headers=practice.admin)).json()["items"][0]

    again = await harness.client.post(
        "/api/billing/export", headers=practice.admin, json={"note_ids": [note_id], "again": True}
    )
    assert again.text == first.text
    later = (await harness.client.get("/api/billing?show=exported", headers=practice.admin)).json()["items"][0]
    assert later["exported_at"] == exported["exported_at"]
    refused = await harness.client.post("/api/billing/export", headers=practice.admin, json={"again": True})
    assert refused.status_code == 422


def test_spreadsheet_formulas_are_neutralised():
    assert safe_cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("99214-25") == "99214-25"
    assert safe_cell(None) == ""
