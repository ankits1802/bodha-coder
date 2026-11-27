from datetime import timedelta

from sqlalchemy import func, select, update

from app.core.db import SessionFactory
from app.models import Practice, Signature, SignatureAdoption, SigningEvent
from tests.api.review_helpers import approve
from tests.builders import maintenance, reviewed_note, sign_in


async def _rows() -> dict[str, int]:
    async with SessionFactory() as db:
        return {
            table.__tablename__: await db.scalar(select(func.count()).select_from(table))
            for table in (SigningEvent, SignatureAdoption, Signature)
        }


async def test_purging_a_practice_removes_its_signatures_seals_and_stored_images(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await approve(harness, practice, note_id)).status_code == 200
    admin_id = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]
    assert await _rows() == {"signing_events": 1, "signature_adoptions": 1, "signatures": 1}
    assert any(key.startswith(f"people/{admin_id}/signatures/") for key in harness.store.objects)
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)
    path = f"/api/hq/practices/{practice.id}"
    await harness.client.patch(path, headers=hq, json={"status": "ended"})
    assert (
        await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    ).status_code == 204
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=2558)
        await db.execute(update(Practice).where(Practice.id == practice.id).values(closed_at=moment))
        await db.commit()

    purged = await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})

    assert purged.status_code == 200, purged.text
    assert await _rows() == {"signing_events": 0, "signature_adoptions": 0, "signatures": 0}
    assert not any(key.startswith(f"people/{admin_id}/") for key in harness.store.objects)
