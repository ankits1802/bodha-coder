from datetime import timedelta

from sqlalchemy import func, select, update

from app.core.db import SessionFactory
from app.models import InboxItem, Practice, QueueView
from app.services.inbox import Notice
from tests.api.inbox_helpers import write_notice
from tests.api.quality_helpers import user_id
from tests.builders import maintenance, practice_with_provider, sign_in

PURGE_AFTER_DAYS = 2558


async def _work_items(practice_id: str) -> tuple[int, int]:
    async with SessionFactory() as db:
        inbox = await db.scalar(select(func.count()).select_from(InboxItem).where(InboxItem.practice_id == practice_id))
        views = await db.scalar(select(func.count()).select_from(QueueView).where(QueueView.practice_id == practice_id))
        return inbox or 0, views or 0


async def test_purging_a_closed_practice_removes_its_inbox_items_and_saved_views(harness):
    practice = await practice_with_provider(harness)
    harbor = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    for place, email in ((practice, "admin@lakeside.example.com"), (harbor, "admin@harbor.example.com")):
        await write_notice(place.id, [await user_id(email)], Notice("plan_ending", payload={"ends_on": "2026-12-01"}))
        saved = await harness.client.post("/api/queue-views", headers=place.admin, json={"name": "Mine", "filters": {}})
        assert saved.status_code == 200, saved.text
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)
    path = f"/api/hq/practices/{practice.id}"
    await harness.client.patch(path, headers=hq, json={"status": "ended"})
    assert (await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})).is_success
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=PURGE_AFTER_DAYS)
        await db.execute(update(Practice).where(Practice.id == practice.id).values(closed_at=moment))
        await db.commit()

    purged = await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})

    assert purged.status_code == 200, purged.text
    assert await _work_items(practice.id) == (0, 0)
    assert await _work_items(harbor.id) == (1, 1)
