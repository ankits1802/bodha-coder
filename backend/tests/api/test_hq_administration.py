from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.models import (
    AccessLog,
    Activity,
    AddendumRequest,
    Analysis,
    Batch,
    CodeSet,
    Decision,
    Note,
    NoteText,
    Practice,
    Provider,
    RecoveryCode,
    Session,
    Suggestion,
    User,
    UserToken,
)
from tests.builders import (
    accept_invite,
    create_hq_user,
    new_practice,
    practice_with_provider,
    read_next_note,
    reviewed_note,
    sign_in,
    upload_note,
)

PRACTICE_ROWS = (Practice, User, Provider, Batch, Note, AddendumRequest, AccessLog, Activity)
NOTE_ROWS = (NoteText, Analysis, Suggestion, Decision, CodeSet)
USER_ROWS = (UserToken, Session, RecoveryCode)


async def _hq(harness) -> dict[str, str]:
    await create_hq_user()
    return await sign_in(harness.client, "hq@bodha.example.com")


async def _owned_ids(practice_id: str) -> tuple[list[str], list[str]]:
    async with SessionFactory() as db:
        note_ids = list((await db.scalars(select(Note.id).where(Note.practice_id == practice_id))).all())
        user_ids = list((await db.scalars(select(User.id).where(User.practice_id == practice_id))).all())
        return note_ids, user_ids


async def _row_counts(practice_id: str, owned: tuple[list[str], list[str]]) -> dict[str, int]:
    note_ids, user_ids = owned
    async with SessionFactory() as db:
        conditions = {
            **{table: (table.id if table is Practice else table.practice_id) == practice_id for table in PRACTICE_ROWS},
            **{table: table.note_id.in_(note_ids) for table in NOTE_ROWS},
            **{table: table.user_id.in_(user_ids) for table in USER_ROWS},
        }
        counts = {}
        for table, condition in conditions.items():
            counts[table.__tablename__] = await db.scalar(select(func.count()).select_from(table).where(condition))
        return counts


async def test_hq_sends_an_invited_admin_a_new_invite_and_an_active_admin_a_reset(harness):
    hq = await _hq(harness)
    lakeside = await new_practice(harness, name="Lakeside", admin_email="admin@lakeside.example.com", hq_headers=hq)
    created = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={
            "name": "Harbor",
            "admin_name": "Harbor Admin",
            "admin_email": "admin@harbor.example.com",
            "plan": "trial",
            "seats": 3,
        },
    )
    harbor = created.json()["id"]
    listed = {row["name"]: row for row in (await harness.client.get("/api/hq/practices", headers=hq)).json()}
    assert [listed["Lakeside"][key] for key in ("admin_name", "admin_email", "admin_status")] == [
        "Practice Admin",
        "admin@lakeside.example.com",
        "active",
    ]
    assert listed["Harbor"]["admin_status"] == "invited"

    reset = await harness.client.post(f"/api/hq/practices/{lakeside}/admin-link", headers=hq)
    assert reset.json() == {"sent": "reset"}
    to, body = harness.messenger.sent[-1]
    assert to == "admin@lakeside.example.com" and "password reset" in body and "/set-password#" in body

    invite = await harness.client.post(f"/api/hq/practices/{harbor}/admin-link", headers=hq)
    assert invite.json() == {"sent": "invite"}
    to, body = harness.messenger.sent[-1]
    assert to == "admin@harbor.example.com" and "invited" in body
    await accept_invite(harness)

    actions = (await harness.client.get("/api/hq/activity", headers=hq)).json()["actions"]
    assert {"admin password reset sent", "admin invite resent"} <= set(actions)


async def test_renewing_adds_a_year_to_the_later_of_today_and_the_renewal_date(harness):
    hq = await _hq(harness)
    practice_id = await new_practice(harness, name="Lakeside", admin_email="admin@lakeside.example.com", hq_headers=hq)
    path = f"/api/hq/practices/{practice_id}"

    await harness.client.patch(path, headers=hq, json={"renews_on": "2099-06-30"})
    assert (await harness.client.post(f"{path}/renew", headers=hq)).json() == {"renews_on": "2100-06-30"}

    await harness.client.patch(path, headers=hq, json={"renews_on": "2020-03-15"})
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    expected = date(today.year + 1, today.month, 28 if (today.month, today.day) == (2, 29) else today.day)
    assert (await harness.client.post(f"{path}/renew", headers=hq)).json() == {"renews_on": expected.isoformat()}
    assert (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]["renews_on"] == expected.isoformat()
    renewed = (await harness.client.get("/api/hq/activity", headers=hq, params={"action": "practice renewed"})).json()
    assert [item["detail"] for item in renewed["items"]] == [f"renews {expected.isoformat()}", "renews 2100-06-30"]


async def _practice_with_every_record(harness, icd_catalog):
    lakeside, note_id = await reviewed_note(harness, icd_catalog)
    decided = await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=lakeside.admin, json={"choices": {"dx:I10": "keep"}}
    )
    assert decided.status_code == 200, decided.text
    asked = await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=lakeside.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage?"}], "channel": "email", "hold": False},
    )
    assert asked.status_code == 200, asked.text
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=lakeside.admin)).status_code == 200
    return lakeside


async def test_deleting_a_practice_removes_its_rows_and_files_and_leaves_others(harness, icd_catalog):
    lakeside = await _practice_with_every_record(harness, icd_catalog)
    harbor = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    assert (await upload_note(harness, harbor)).status_code == 200
    await read_next_note(harness, icd_catalog)
    owned, harbor_owned = await _owned_ids(lakeside.id), await _owned_ids(harbor.id)
    before = await _row_counts(lakeside.id, owned)
    assert all(count > 0 for count in before.values()), before
    harbor_before = await _row_counts(harbor.id, harbor_owned)

    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=lakeside.secrets)
    path = f"/api/hq/practices/{lakeside.id}"
    refused = await harness.client.request("DELETE", path, headers=hq, json={"confirm_name": "Lakeside"})
    assert refused.status_code == 409
    await harness.client.patch(path, headers=hq, json={"status": "blocked"})
    misnamed = await harness.client.request("DELETE", path, headers=hq, json={"confirm_name": "lakeside"})
    assert misnamed.status_code == 422

    deleted = await harness.client.request("DELETE", path, headers=hq, json={"confirm_name": "Lakeside"})
    assert deleted.status_code == 204, deleted.text
    assert await _row_counts(lakeside.id, owned) == {**{name: 0 for name in before}, "activity": 1}
    assert await _row_counts(harbor.id, harbor_owned) == harbor_before
    assert not any(key.startswith(f"practices/{lakeside.id}/") for key in harness.store.objects)
    assert any(key.startswith(f"practices/{harbor.id}/") for key in harness.store.objects)
    trail = (await harness.client.get("/api/hq/activity", headers=hq, params={"practice_id": lakeside.id})).json()
    assert [(item["action"], item["detail"]) for item in trail["items"]] == [("practice deleted", "Lakeside")]
    assert (await harness.client.get("/api/today", headers=lakeside.admin)).status_code == 401
    assert (await harness.client.get("/api/today", headers=harbor.admin)).status_code == 200
    gone = await harness.client.request("DELETE", path, headers=hq, json={"confirm_name": "Lakeside"})
    assert gone.status_code == 404
