from datetime import date

import pytest
from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import Note
from tests.api.claim_helpers import DETAILS, MEDICARE, access_entries, approved_note, ok, second_approved_note
from tests.builders import invite_member, reviewed_note, sign_in

SAVED = {
    **DETAILS,
    "member_id": "1EG4-TE5-MK72",
    "street_2": None,
    "group_number": None,
    "subscriber_last": None,
    "subscriber_first": None,
}


def _path(note_id: str) -> str:
    return f"/api/notes/{note_id}/claim-details"


async def test_details_start_from_what_the_note_read_and_are_confirmed_by_a_person(harness, icd_catalog):
    practice, note_id = await approved_note(harness, icd_catalog)

    shown = ok(await harness.client.get(_path(note_id), headers=practice.admin))

    assert shown == {
        "details": None,
        "suggested": {
            "source": "note",
            "patient_name": "Reyes Marisol",
            "patient_birth_date": None,
            "patient_sex": "F",
        },
    }
    saved = ok(await harness.client.put(_path(note_id), headers=practice.admin, json=DETAILS))
    record = saved["details"]
    assert {key: record[key] for key in SAVED} == SAVED
    assert (record["revision"], record["confirmed_by"], saved["suggested"]) == (1, "Practice Admin", None)
    again = ok(
        await harness.client.put(_path(note_id), headers=practice.admin, json={**DETAILS, "street": "10 Elm St"})
    )
    assert (again["details"]["revision"], again["details"]["street"]) == (2, "10 Elm St")
    assert ok(await harness.client.get(_path(note_id), headers=practice.admin))["details"]["revision"] == 2
    logged = [(entry.action, entry.note_id, entry.detail) for entry in await access_entries(practice)]
    assert logged.count(("saved claim details", note_id, None)) == 2
    assert logged.count(("opened claim details", note_id, None)) == 2


async def test_an_earlier_claim_for_the_same_patient_fills_the_rest(harness, icd_catalog):
    practice, first = await approved_note(harness, icd_catalog)
    ok(await harness.client.put(_path(first), headers=practice.admin, json=DETAILS))
    second = await second_approved_note(harness, icd_catalog, practice)
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == second).values(patient_birth_date=date(1959, 3, 12)))
        await db.commit()

    suggested = ok(await harness.client.get(_path(second), headers=practice.admin))["suggested"]

    assert suggested["source"] == "earlier_claim"
    assert (suggested["member_id"], suggested["patient_last"], suggested["patient_first"]) == (
        "1EG4-TE5-MK72",
        "Reyes",
        "Marisol",
    )
    assert (suggested["street"], suggested["zip_code"], suggested["relationship"]) == ("9 Elm St", "62704", "18")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"relationship": "01"}, "name the subscriber when the patient is not the subscriber"),
        ({"patient_birth_date": "2026-12-01"}, "the birth date must fall before the date of service"),
        ({"state": "ZZ"}, "ZZ is not a US state or territory"),
        ({"member_id": "1EG4*TE5"}, "the member ID holds characters a claim cannot carry"),
        ({"zip_code": "6270x"}, "the ZIP code holds characters a claim cannot carry"),
    ],
)
async def test_details_are_checked_before_they_are_kept(harness, icd_catalog, changes, message):
    practice, note_id = await approved_note(harness, icd_catalog)

    refused = await harness.client.put(_path(note_id), headers=practice.admin, json={**DETAILS, **changes})

    assert (refused.status_code, refused.json()["message"]) == (422, message)


async def test_details_belong_to_approved_visits(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)

    refused = await harness.client.get(_path(note_id), headers=practice.admin)

    assert (refused.status_code, refused.json()["message"]) == (409, "claim details belong to approved visits")


async def test_billers_keep_claim_details_and_set_the_payer_but_coders_cannot(harness, icd_catalog):
    practice, note_id = await approved_note(harness, icd_catalog)
    payer = ok(await harness.client.post("/api/practice/payers", headers=practice.admin, json=MEDICARE))
    await invite_member(harness, practice, name="Bea Biller", email="biller@lakeside.example.com", role="biller")
    await invite_member(harness, practice, name="Cole Coder", email="coder@lakeside.example.com", role="coder")
    biller = await sign_in(harness.client, "biller@lakeside.example.com", secret_box=practice.secrets)
    coder = await sign_in(harness.client, "coder@lakeside.example.com", secret_box=practice.secrets)

    saved = ok(await harness.client.put(_path(note_id), headers=biller, json=DETAILS))

    assert saved["details"]["confirmed_by"] == "Bea Biller"
    chosen = ok(await harness.client.put(f"/api/notes/{note_id}/payer", headers=biller, json={"payer": payer["id"]}))
    assert chosen == {"payer": payer["id"]}
    assert (await harness.client.get(_path(note_id), headers=coder)).status_code == 403
