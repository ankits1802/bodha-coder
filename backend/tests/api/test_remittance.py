from __future__ import annotations

import hashlib
from datetime import date
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import AccessLog, Practice, Remittance
from app.services.remittance_835 import Adjustment, ServicePayment, parse_835
from app.services.remittance_outcomes import line_outcome
from app.services.x12 import X12Invalid
from tests.api.remittance_helpers import BODY, FILE_NAME, era, post_era, three_notes
from tests.builders import practice_with_member, practice_with_provider, sign_in


async def test_an_835_is_stored_matched_and_classified(harness):
    practice = await practice_with_provider(harness)
    reyes, okafor, lindqvist = await three_notes(harness, practice)
    data = era(reyes, lindqvist)

    uploaded = await post_era(harness, practice.admin, data)
    assert uploaded.status_code == 200, uploaded.text
    remittance_id = uploaded.json()["ids"][0]
    assert uploaded.json()["counts"] == {"downcoded": 1, "paid_as_billed": 1, "denied": 1, "unmatched": 1}
    assert harness.store.objects[f"practices/{practice.id}/remittances/{remittance_id}.835"] == data

    detail = (await harness.client.get(f"/api/remittances/{remittance_id}", headers=practice.admin)).json()
    assert (detail["remittance"]["payer"], detail["remittance"]["paid_on"]) == ("ACME HEALTH PLAN", "2026-11-24")
    rows = [
        (line["status"], line["note_id"], line["billed_code"], line["paid_code"], line["appeal_by"])
        for line in detail["lines"]
    ]
    assert rows == [
        ("downcoded", reyes, "99215", "99214", "2027-03-24"),
        ("paid_as_billed", okafor, "99213", "99213", None),
        ("denied", lindqvist, "99214", "99214", "2027-05-23"),
        ("unmatched", None, "99212", "99212", "2027-05-23"),
    ]
    first = detail["lines"][0]
    assert (first["billed_amount"], first["paid_amount"], first["patient_name"]) == (20000, 9000, "Marisol Reyes")
    assert first["adjustments"] == [
        {"group": "CO", "reason": "45", "cents": 8000},
        {"group": "PR", "reason": "2", "cents": 3000},
    ]


async def test_lines_filter_by_status_and_the_list_shows_counts(harness):
    practice = await practice_with_provider(harness)
    reyes, _, lindqvist = await three_notes(harness, practice)
    remittance_id = (await post_era(harness, practice.admin, era(reyes, lindqvist))).json()["ids"][0]

    downcoded = await harness.client.get(
        f"/api/remittances/{remittance_id}", headers=practice.admin, params={"status": "downcoded"}
    )
    assert [line["note_id"] for line in downcoded.json()["lines"]] == [reyes]
    listing = (await harness.client.get("/api/remittances", headers=practice.admin)).json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert (item["file_name"], item["uploaded_by"], item["next_appeal_by"]) == (
        FILE_NAME,
        "Practice Admin",
        "2027-03-24",
    )
    assert item["counts"] == {"downcoded": 1, "paid_as_billed": 1, "denied": 1, "unmatched": 1}


async def test_the_appeal_draft_names_the_claim_and_links_the_defense_packet(harness):
    practice = await practice_with_provider(harness)
    reyes, okafor, lindqvist = await three_notes(harness, practice)
    remittance_id = (await post_era(harness, practice.admin, era(reyes, lindqvist))).json()["ids"][0]
    lines = (await harness.client.get(f"/api/remittances/{remittance_id}", headers=practice.admin)).json()["lines"]

    draft = await harness.client.get(f"/api/remittances/lines/{lines[0]['id']}/appeal", headers=practice.admin)
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["defense_packet"] == f"/api/notes/{reyes}/defense-packet"
    assert body["appeal_by"] == "2027-03-24"
    text = body["text"]
    for expected in (
        "Re: Request for redetermination",
        "Patient: Marisol Reyes",
        "Member ID: MBI0001",
        "Payer claim number: PCN0001",
        "Date of service: 20 November 2026",
        "Rendering provider: Elena Varga, MD, NPI 1234567893",
        "Billed: 99215 $200.00",
        "Paid: 99214 $90.00",
        "PR-2 Coinsurance Amount",
        "The service billed as 99215 was paid as 99214.",
    ):
        assert expected in text

    denied = (
        await harness.client.get(f"/api/remittances/lines/{lines[2]['id']}/appeal", headers=practice.admin)
    ).json()
    assert "Re: Request for reconsideration" in denied["text"]
    assert "of the denial of this service" in denied["text"]
    paid = await harness.client.get(f"/api/remittances/lines/{lines[1]['id']}/appeal", headers=practice.admin)
    assert paid.status_code == 409


async def test_uploads_views_and_drafts_are_in_the_access_log(harness):
    practice = await practice_with_provider(harness)
    reyes, _, lindqvist = await three_notes(harness, practice)
    remittance_id = (await post_era(harness, practice.admin, era(reyes, lindqvist))).json()["ids"][0]
    lines = (await harness.client.get(f"/api/remittances/{remittance_id}", headers=practice.admin)).json()["lines"]
    await harness.client.get(f"/api/remittances/lines/{lines[0]['id']}/appeal", headers=practice.admin)

    async with SessionFactory() as db:
        actions = (
            await db.scalars(
                select(AccessLog.action)
                .where(AccessLog.action.in_(("uploaded remittance", "viewed remittance", "drafted appeal")))
                .order_by(AccessLog.created_at)
            )
        ).all()
        drafted = await db.scalar(select(AccessLog.note_id).where(AccessLog.action == "drafted appeal"))
    assert list(actions) == ["uploaded remittance", "viewed remittance", "drafted appeal"]
    assert drafted == reyes


async def test_the_same_file_twice_is_refused_and_a_coder_cannot_upload(harness):
    practice = await practice_with_member(harness, name="Cody Coder", email="cody@lakeside.example.com", role="coder")
    data = era()
    assert (await post_era(harness, practice.admin, data)).status_code == 200
    again = await post_era(harness, practice.admin, data)
    assert again.status_code == 409
    coder = await sign_in(harness.client, "cody@lakeside.example.com")
    assert (await post_era(harness, coder, era(), "other.835")).status_code == 403


async def test_a_repeat_is_recognised_by_its_checksum_whatever_its_name(harness):
    practice = await practice_with_provider(harness)
    data = era()
    first_id = (await post_era(harness, practice.admin, data)).json()["ids"][0]
    async with SessionFactory() as db:
        first = await db.get_one(Remittance, first_id)
        zone = ZoneInfo(await db.scalar(select(Practice.time_zone).where(Practice.id == practice.id)))
    assert first.file_sha256 == hashlib.sha256(data).hexdigest()
    uploaded_on = first.created_at.astimezone(zone).strftime("%d %b %Y")

    renamed = await post_era(harness, practice.admin, data, "copy-from-the-clearinghouse.835")
    assert renamed.status_code == 409
    assert renamed.json()["message"] == f"this file was already uploaded on {uploaded_on} as {FILE_NAME}"
    other = await post_era(harness, practice.admin, era("ACCT2001", "ACCT2003"), FILE_NAME)
    assert other.status_code == 200, other.text


async def test_an_upload_from_before_checksums_is_recognised_and_given_its_checksum(harness):
    practice = await practice_with_provider(harness)
    data = era()
    first_id = (await post_era(harness, practice.admin, data)).json()["ids"][0]
    async with SessionFactory() as db:
        await db.execute(update(Remittance).where(Remittance.id == first_id).values(file_sha256=None))
        await db.commit()

    assert (await post_era(harness, practice.admin, data, "renamed.835")).status_code == 409
    async with SessionFactory() as db:
        stored = await db.scalar(select(Remittance.file_sha256).where(Remittance.id == first_id))
    assert stored == hashlib.sha256(data).hexdigest()


async def test_a_broken_file_is_refused_with_the_reason(harness):
    practice = await practice_with_provider(harness)
    broken = era(body=BODY.replace("SE*29*0001~", "SE*28*0001~"))
    response = await post_era(harness, practice.admin, broken)
    assert response.status_code == 422
    assert response.json()["message"] == "SE counts 28 but there are 29"


def test_the_parser_reads_the_envelope_and_the_service_lines():
    advice = parse_835(era())[0]
    assert (advice.payer_name, advice.payer_id, advice.paid_on, advice.total_cents) == (
        "ACME HEALTH PLAN",
        "ACME01",
        date(2026, 11, 24),
        17500,
    )
    assert [claim.claim_ref for claim in advice.claims] == ["ACCT1001", "ACCT1002", "ACCT1003", "ACCT9999"]
    first = advice.claims[0]
    assert (first.status, first.filing_indicator, first.payer_claim_number, first.member_id) == (
        "1",
        "MB",
        "PCN0001",
        "MBI0001",
    )
    assert first.lines[0].billed_code == "99215" and first.lines[0].paid_code == "99214"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("CAS*CO*45*35~", "CAS*CO*45*30~"), "does not balance (SVC02 - CAS != SVC03)"),
        (("BPR*I*175*", "BPR*I*176*"), "does not balance: claims paid minus PLB differs from BPR02"),
        (("DTM*472*20261121~", "DTM*472*20261131~"), "DTM02 20261131 is not a date (CCYYMMDD)"),
        (("GE*1*1~", "GE*1*2~"), "GE control number 2 does not match 1"),
    ],
)
def test_the_parser_refuses_a_file_that_does_not_add_up(change, message):
    with pytest.raises(X12Invalid) as refused:
        parse_835(era(body=BODY.replace(*change)))
    assert message in refused.value.message


def test_a_file_without_an_isa_header_is_refused():
    with pytest.raises(X12Invalid):
        parse_835(b"GS*HP*X*Y*20261124*1200*1*X*005010X221A1~")


def _line(paid_code: str, paid: int, *adjustments: Adjustment) -> ServicePayment:
    return ServicePayment("99214", paid_code, 15000, paid, date(2026, 11, 20), adjustments)


def test_a_downcode_reason_on_the_same_code_counts_as_downcoded():
    line = _line("99214", 9000, Adjustment("CO", "150", 6000))
    assert line_outcome(line, "1") == "downcoded"


def test_a_visit_left_to_the_deductible_is_not_a_denial():
    line = _line("99214", 0, Adjustment("CO", "45", 3000), Adjustment("PR", "1", 12000))
    assert line_outcome(line, "1") == "paid_as_billed"


def test_a_higher_paid_code_is_not_a_downcode():
    assert line_outcome(_line("99215", 15000), "1") == "matched"
