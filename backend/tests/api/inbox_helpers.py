from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import InboxItem
from app.services.inbox import Notice, notify
from tests.builders import Harness

QUESTION = {"key": "dx:N18.30", "text": "What stage is the kidney disease?"}
CODER_EMAIL = "cora@lakeside.example.com"


async def inbox_of(harness: Harness, headers: dict[str, str], *, offset: int = 0) -> dict[str, Any]:
    response = await harness.client.get("/api/inbox", headers=headers, params={"offset": offset})
    assert response.status_code == 200, response.text
    return response.json()


def entries(page: dict[str, Any]) -> list[tuple[str, str, str | None, dict[str, Any]]]:
    return [(item["kind"], item["actor_name"], item["note_id"], item["payload"]) for item in page["items"]]


async def stored_items() -> list[InboxItem]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(InboxItem).order_by(InboxItem.created_at, InboxItem.id))).all())


async def write_notice(practice_id: str, user_ids: Iterable[str], notice: Notice) -> int:
    async with SessionFactory() as db:
        items = await notify(db, practice_id, user_ids, notice)
        await db.commit()
        return len(items)


async def ask_provider(harness: Harness, headers: dict[str, str], note_id: str) -> str:
    response = await harness.client.post(
        f"/api/notes/{note_id}/ask", headers=headers, json={"questions": [QUESTION], "channel": "email"}
    )
    assert response.status_code == 200, response.text
    return harness.messenger.last_fragment()
