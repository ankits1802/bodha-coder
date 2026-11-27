import csv
import hashlib
import io
from datetime import timedelta

import pytest
from sqlalchemy import Integer, String, bindparam, func, select, text, update
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.models import AccessLog, Activity, Analysis, Decision, Note, Practice, PracticeMembership
from tests.builders import maintenance, practice_with_provider, read_next_note, reviewed_note, sign_in, upload_note

KEPT_TABLES = (Note, Analysis, Decision, PracticeMembership, AccessLog)
PURGE = text("SELECT bodha_purge_practice(:practice, :days)").bindparams(
    bindparam("practice", type_=String), bindparam("days", type_=Integer)
)


async def _counts(practice_id: str) -> dict[str, int]:
    notes = select(Note.id).where(Note.practice_id == practice_id)
    conditions = {
        Note: Note.practice_id == practice_id,
        Analysis: Analysis.note_id.in_(notes),
        Decision: Decision.note_id.in_(notes),
        PracticeMembership: PracticeMembership.practice_id == practice_id,
        AccessLog: AccessLog.practice_id == practice_id,
    }
    async with SessionFactory() as db:
        return {
            table.__tablename__: await db.scalar(select(func.count()).select_from(table).where(condition))
            for table, condition in conditions.items()
        }


async def _backdate_closure(practice_id: str, days: int) -> None:
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=days)
        await db.execute(update(Practice).where(Practice.id == practice_id).values(closed_at=moment))
        await db.commit()


async def _closed_practice(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=practice.admin, json={"choices": {"dx:I10": "keep"}}
    )
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)
    path = f"/api/hq/practices/{practice.id}"
    assert (
        await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    ).status_code == 409
    await harness.client.patch(path, headers=hq, json={"status": "ended"})
    misnamed = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "lakeside"})
    assert misnamed.status_code == 422
    return practice, hq, path


async def test_closing_a_practice_signs_everyone_out_and_keeps_every_record_and_file(harness, icd_catalog):
    practice, hq, path = await _closed_practice(harness, icd_catalog)
    before, files = await _counts(practice.id), set(harness.store.objects)

    closed = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})

    assert closed.status_code == 204, closed.text
    assert (await harness.client.get("/api/today", headers=practice.admin)).status_code == 401
    assert await _counts(practice.id) == before
    assert set(harness.store.objects) == files
    async with SessionFactory() as db:
        ends = await db.scalars(
            select(PracticeMembership.ended_at).where(PracticeMembership.practice_id == practice.id)
        )
        assert all(ended is not None for ended in ends.all())
    row = (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]
    closed_on = (await _closed_at(practice.id)).date()
    assert (row["status"], row["closed_at"][:10]) == ("closed", closed_on.isoformat())
    assert row["purge_after"] == (closed_on + timedelta(days=2557)).isoformat()
    assert (await harness.client.patch(path, headers=hq, json={"seats": 3})).status_code == 409
    trail = (await harness.client.get("/api/hq/activity", headers=hq, params={"action": "practice closed"})).json()
    assert [item["detail"] for item in trail["items"]] == ["Lakeside"]


async def _closed_at(practice_id: str):
    async with SessionFactory() as db:
        return await db.scalar(select(Practice.closed_at).where(Practice.id == practice_id))


async def test_a_practice_is_purged_only_2557_days_after_closing_and_its_access_log_is_exported(harness, icd_catalog):
    practice, hq, path = await _closed_practice(harness, icd_catalog)
    harbor = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    assert (await upload_note(harness, harbor)).status_code == 200
    await read_next_note(harness, icd_catalog)
    harbor_before = await _counts(harbor.id)
    await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    entries = (await _counts(practice.id))["access_log"]

    assert (
        await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})
    ).status_code == 409
    await _backdate_closure(practice.id, 2556)
    assert (
        await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})
    ).status_code == 409
    await _backdate_closure(practice.id, 2558)
    purged = await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})

    assert purged.status_code == 200, purged.text
    archive = harness.store.objects[f"archives/practices/{practice.id}/access-log.csv"]
    assert purged.json() == {"access_log_entries": entries, "access_log_sha256": hashlib.sha256(archive).hexdigest()}
    rows = list(csv.reader(io.StringIO(archive.decode("utf-8"))))
    assert (rows[0][-3:], len(rows) - 1) == (["chain_seq", "prev_hash", "row_hash"], entries)
    assert await _counts(practice.id) == {table.__tablename__: 0 for table in KEPT_TABLES}
    assert await _counts(harbor.id) == harbor_before
    assert not any(key.startswith(f"practices/{practice.id}/") for key in harness.store.objects)
    async with SessionFactory() as db:
        status = await db.scalar(select(Practice.status).where(Practice.id == practice.id))
        actions = set((await db.scalars(select(Activity.action).where(Activity.practice_id == practice.id))).all())
    assert status == "purged"
    listed = {row["id"]: row for row in (await harness.client.get("/api/hq/practices", headers=hq)).json()}
    assert (listed[practice.id]["status"], listed[practice.id]["purged_at"] is not None) == ("purged", True)
    assert {"practice closed", "practice purged", "practice updated"} <= actions
    assert (await harness.client.post("/api/hq/audit-log/verify", headers=hq)).json()["intact"] is True


async def test_the_database_refuses_an_early_purge_even_when_asked_directly(harness, icd_catalog):
    practice, hq, path = await _closed_practice(harness, icd_catalog)
    await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="closed less than 2557 days ago"):
            await db.scalar(PURGE, {"practice": practice.id, "days": 0})


async def test_closing_is_final_in_the_database(harness, icd_catalog):
    practice, hq, path = await _closed_practice(harness, icd_catalog)
    await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="closing a practice is final"):
            await db.execute(update(Practice).where(Practice.id == practice.id).values(closed_at=None))


async def test_a_closed_practice_takes_no_new_admin_renewal_or_edit(harness, icd_catalog):
    practice, hq, path = await _closed_practice(harness, icd_catalog)
    await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    appointment = {"name": "Lee Park", "email": "lee@lakeside.example.com", "reason": "practice owner asked by email"}

    added = await harness.client.post(f"{path}/admins", headers=hq, json=appointment)
    renewed = await harness.client.post(f"{path}/renew", headers=hq, json={"until": "2099-01-31"})
    edited = await harness.client.patch(path, headers=hq, json={"seats": 4})

    assert (added.status_code, renewed.status_code, edited.status_code) == (409, 409, 409)
