import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.models import AccessLog, Activity, Analysis, Decision, utcnow
from tests.builders import maintenance, practice_with_provider, reviewed_note, sign_in

ZERO = "0" * 64
LONG_AGO = datetime(2001, 1, 1, tzinfo=UTC)


def _utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _link(prev: str, values: list) -> str:
    return hashlib.sha256((prev + json.dumps(values, ensure_ascii=False)).encode("utf-8")).hexdigest()


def _access_values(row: AccessLog) -> list:
    return [
        row.id,
        row.practice_id,
        row.chain_seq,
        _utc(row.created_at),
        row.actor_kind,
        row.actor_id,
        row.actor_name,
        row.action,
        row.note_id,
        row.detail,
        row.ip,
        row.user_agent,
    ]


async def _entries(practice_id: str) -> list[AccessLog]:
    async with SessionFactory() as db:
        query = select(AccessLog).where(AccessLog.practice_id == practice_id).order_by(AccessLog.chain_seq)
        return list((await db.scalars(query)).all())


async def _hq(harness, practice) -> dict[str, str]:
    return await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)


async def test_each_access_log_entry_is_stamped_by_the_database_and_linked_to_the_one_before(harness):
    practice = await practice_with_provider(harness)
    async with SessionFactory() as db:
        db.add(
            AccessLog(
                practice_id=practice.id,
                actor_kind="system",
                actor_id="bodha",
                actor_name="Bodha",
                action="opened note",
                created_at=LONG_AGO,
            )
        )
        await db.commit()

    entries = await _entries(practice.id)

    assert [entry.chain_seq for entry in entries] == list(range(1, len(entries) + 1))
    assert utcnow() - entries[-1].created_at < timedelta(minutes=5)
    prev = ZERO
    for entry in entries:
        assert (entry.prev_hash, entry.row_hash) == (prev, _link(prev, _access_values(entry)))
        prev = entry.row_hash


async def _practice_with_two_entries(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.get("/api/access-log", headers=practice.admin)).status_code == 200
    assert len(await _entries(practice.id)) >= 2
    return practice


async def test_hq_verification_names_the_first_broken_link(harness):
    practice = await _practice_with_two_entries(harness)
    hq = await _hq(harness, practice)
    first = (await harness.client.post("/api/hq/audit-log/verify", headers=hq)).json()
    assert first["intact"] is True
    assert {chain["chain"] for chain in first["chains"]} == {"activity", "access_log"}
    target = (await _entries(practice.id))[1]
    async with SessionFactory() as db:
        await maintenance(db)
        await db.execute(update(AccessLog).where(AccessLog.id == target.id).values(detail="edited"))
        await db.commit()

    found = (await harness.client.post("/api/hq/audit-log/verify", headers=hq)).json()

    broken = [chain for chain in found["chains"] if not chain["intact"]]
    assert found["intact"] is False
    assert [(chain["practice_id"], chain["broken_seq"], chain["broken_id"], chain["problem"]) for chain in broken] == [
        (practice.id, 2, target.id, "changed row")
    ]
    assert broken[0]["practice_name"] == "Lakeside"
    trail = (await harness.client.get("/api/hq/activity", headers=hq, params={"action": "audit log verified"})).json()
    assert trail["items"][0]["detail"].startswith("1 of ")


async def test_a_removed_entry_shows_as_missing_rows(harness):
    practice = await _practice_with_two_entries(harness)
    hq = await _hq(harness, practice)
    target = (await _entries(practice.id))[0]
    async with SessionFactory() as db:
        await maintenance(db)
        await db.execute(delete(AccessLog).where(AccessLog.id == target.id))
        await db.commit()

    found = (await harness.client.post("/api/hq/audit-log/verify", headers=hq)).json()

    problems = {(chain["practice_id"], chain["problem"], chain["broken_seq"]) for chain in found["chains"]}
    assert (practice.id, "missing rows", 2) in problems


async def test_only_hq_verifies_the_audit_log(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post("/api/hq/audit-log/verify", headers=practice.admin)).status_code == 403


@pytest.mark.parametrize(
    "statement",
    [
        update(AccessLog).values(detail="x"),
        delete(AccessLog),
        update(Activity).values(detail="x"),
        delete(Activity),
        update(Decision).values(choice="keep"),
        delete(Decision),
        text("TRUNCATE access_log CASCADE"),
    ],
)
async def test_kept_rows_cannot_be_changed_or_removed(harness, icd_catalog, statement):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=practice.admin, json={"choices": {"dx:I10": "keep"}}
    )
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="refused"):
            await db.execute(statement)


async def test_a_stored_ai_result_is_written_once(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    async with SessionFactory() as db:
        await db.execute(update(Analysis).where(Analysis.note_id == note_id).values(status="superseded"))
        with pytest.raises(DBAPIError, match="written once"):
            await db.execute(update(Analysis).where(Analysis.note_id == note_id).values(report={"em": None}))


async def test_hq_changes_are_chained_in_the_activity_record(harness):
    practice = await practice_with_provider(harness)
    hq = await _hq(harness, practice)
    await harness.client.patch(f"/api/hq/practices/{practice.id}", headers=hq, json={"seats": 11})
    async with SessionFactory() as db:
        rows = list((await db.scalars(select(Activity).order_by(Activity.chain_seq))).all())

    assert [row.chain_seq for row in rows] == list(range(1, len(rows) + 1))
    assert rows[0].prev_hash == ZERO
    assert all(later.prev_hash == earlier.row_hash for earlier, later in zip(rows, rows[1:], strict=False))
    assert rows[-1].changes == [{"field": "seats", "before": 10, "after": 11}]
