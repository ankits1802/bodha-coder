import csv
import io
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import Note
from tests.builders import invite_member, reviewed_note, sign_in

COMPLIANCE = {"name": "Jordan Diaz", "email": "jordan@lakeside.example.com", "role": "compliance"}
CODER = {"name": "Priya Nair", "email": "priya@lakeside.example.com", "role": "coder"}
BIRTH = date(1959, 3, 2)
HEADER = [
    "at",
    "actor",
    "actor_kind",
    "action",
    "note_id",
    "detail",
    "ip",
    "user_agent",
    "chain_seq",
    "prev_hash",
    "row_hash",
]


def _today() -> date:
    return datetime.now(ZoneInfo("America/Chicago")).date()


async def _rows(harness, headers, **params) -> set[tuple[str, str | None]]:
    page = await harness.client.get("/api/access-log", headers=headers, params=params)
    assert page.status_code == 200, page.text
    return {(row["action"], row["note_id"]) for row in page.json()["items"]}


async def _opened_note(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).status_code == 200
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == note_id).values(patient_birth_date=BIRTH))
        await db.commit()
    return practice, note_id


async def test_the_access_log_filters_by_note_patient_person_action_and_days(harness, icd_catalog):
    practice, note_id = await _opened_note(harness, icd_catalog)
    me = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]

    by_note = await _rows(harness, practice.admin, note_id=note_id)

    assert ("opened note", note_id) in by_note and {found for _, found in by_note} == {note_id}
    assert await _rows(harness, practice.admin, patient="marisol") == by_note
    assert await _rows(harness, practice.admin, birth_date=BIRTH.isoformat()) == by_note
    assert await _rows(harness, practice.admin, birth_date="1960-01-01") == set()
    assert await _rows(harness, practice.admin, patient="nobody") == set()
    assert await _rows(harness, practice.admin, action="opened note") == {("opened note", note_id)}
    assert ("opened note", note_id) in await _rows(harness, practice.admin, user_id=me)
    assert await _rows(harness, practice.admin, user_id="someone-else") == set()
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    assert await _rows(harness, practice.admin, start=tomorrow) == set()
    week = {"start": (_today() - timedelta(days=7)).isoformat(), "end": _today().isoformat()}
    assert ("opened note", note_id) in await _rows(harness, practice.admin, **week)
    backwards = await harness.client.get(
        "/api/access-log", headers=practice.admin, params={"start": week["end"], "end": week["start"]}
    )
    assert backwards.status_code == 422


async def test_the_access_log_names_the_people_seen_in_the_range(harness, icd_catalog):
    practice, _ = await _opened_note(harness, icd_catalog)
    me = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]

    page = (await harness.client.get("/api/access-log", headers=practice.admin)).json()

    assert {"id": me, "name": "Practice Admin"} in page["people"]
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    later = (await harness.client.get("/api/access-log", headers=practice.admin, params={"start": tomorrow})).json()
    assert later["people"] == []


async def test_viewing_the_access_log_is_logged_without_the_patient_searched_for(harness, icd_catalog):
    practice, _ = await _opened_note(harness, icd_catalog)
    await _rows(harness, practice.admin, patient="Marisol")

    page = await harness.client.get("/api/access-log", headers=practice.admin, params={"action": "viewed access log"})
    details = [row["detail"] for row in page.json()["items"]]

    assert details == [f"{_today().isoformat()} to {_today().isoformat()}; by patient"]
    assert "Marisol" not in details[0]


async def test_compliance_exports_the_access_log_and_the_export_is_logged(harness, icd_catalog):
    practice, note_id = await _opened_note(harness, icd_catalog)
    await invite_member(harness, practice, **COMPLIANCE)
    compliance = await sign_in(harness.client, COMPLIANCE["email"], secret_box=practice.secrets)

    exported = await harness.client.post("/api/access-log/export", headers=compliance, json={"note_id": note_id})

    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(exported.text)))
    assert rows[0] == HEADER
    assert {(row[3], row[4]) for row in rows[1:]} >= {("opened note", note_id)}
    logged = await harness.client.get("/api/access-log", headers=compliance, params={"action": "exported access log"})
    assert [row["detail"] for row in logged.json()["items"]] == [
        f"{len(rows) - 1} entries; {_today().isoformat()} to {_today().isoformat()}; by note"
    ]


async def test_people_outside_admin_and_compliance_cannot_read_the_access_log(harness, icd_catalog):
    practice, _ = await _opened_note(harness, icd_catalog)
    await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])
    assert (await harness.client.get("/api/access-log", headers=coder)).status_code == 403
    assert (await harness.client.post("/api/access-log/export", headers=coder, json={})).status_code == 403
