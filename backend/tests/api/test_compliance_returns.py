import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.services.approval import RETURNED_ALONE, UNDECIDED_RETURN
from tests.api.inbox_helpers import entries, inbox_of, stored_items
from tests.api.return_helpers import (
    CODER,
    FLAG,
    RETURN,
    compliance_member,
    decide_again,
    flag,
    note_at_risk,
    send_back,
    stored_returns,
)
from tests.api.review_helpers import approve, note_detail
from tests.builders import invite_member, reviewed_note, sign_in

RETURNED_ITEMS = ["dx:E11.9", "dx:I10", "dx:I12.9", "dx:N18.30", "dx:R20.2", "em"]
SAID = "Level not supported: Exam repeated from the last visit"


async def test_a_return_needs_a_structured_reason(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await flag(harness, practice.admin, note_id)
    compliance = await compliance_member(harness, practice)

    assert (await send_back(harness, compliance, note_id, None)).status_code == 422
    assert (await send_back(harness, compliance, note_id, {"reason": "other"})).status_code == 422
    assert (await send_back(harness, compliance, note_id, {"reason": "looks_fine"})).status_code == 422
    assert await stored_returns(note_id) == []
    assert (await send_back(harness, compliance, note_id)).status_code == 200


async def test_a_return_keeps_its_reason_the_cleared_flag_and_the_items_to_decide_again(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await flag(harness, practice.admin, note_id)
    compliance = await compliance_member(harness, practice)

    assert (await send_back(harness, compliance, note_id)).status_code == 200

    [stored] = await stored_returns(note_id)
    assert (stored.reason, stored.note, stored.flag_reason, stored.actor_role) == (
        RETURN["reason"],
        RETURN["note"],
        FLAG,
        "compliance",
    )
    assert sorted(stored.finding_keys) == RETURNED_ITEMS
    detail = await note_detail(harness, practice, note_id)
    [record] = detail["history"]["returns"]
    assert {key: value for key, value in record.items() if key != "at"} == {
        "reason": "level_not_supported",
        "note": RETURN["note"],
        "by": "Jordan Diaz",
        "role": "compliance",
        "flag_reason": FLAG,
    }
    returned = detail["note"]["returned"]
    assert (returned["reason"], returned["note"], returned["by"], returned["items"]) == (
        "level_not_supported",
        RETURN["note"],
        "Jordan Diaz",
        6,
    )
    last = detail["history"]["changes"][-1]
    assert (last["field"], last["old"], last["new"], last["reason"], last["by"]) == (
        "flag",
        FLAG,
        None,
        SAID,
        "Jordan Diaz",
    )


async def test_a_returned_note_is_approved_only_after_a_fresh_decision_on_each_returned_item(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await flag(harness, practice.admin, note_id)
    compliance = await compliance_member(harness, practice)
    await send_back(harness, compliance, note_id)

    detail = await note_detail(harness, practice, note_id)
    assert (detail["note"]["lane"], detail["note"]["lane_reason"], detail["note"]["headline"]) == (
        "coder",
        "returned",
        "Returned",
    )
    assert sorted(item["key"] for item in detail["findings"] if item["decide_again"]) == RETURNED_ITEMS
    refused = await approve(harness, practice, note_id)
    assert (refused.status_code, refused.json()["message"]) == (409, UNDECIDED_RETURN)

    decided = await decide_again(harness, practice, detail)
    assert decided.status_code == 200, decided.text
    assert not any(item["decide_again"] for item in decided.json()["findings"])
    assert decided.json()["note"]["lane_reason"] == "returned"
    approved = await approve(harness, practice, note_id)
    assert approved.status_code == 200, approved.text
    assert (await note_detail(harness, practice, note_id))["note"]["returned"] is None


async def test_a_critical_risk_alone_returns_to_the_coder_and_is_never_approved_in_bulk(harness, icd_catalog):
    practice, note_id = await note_at_risk(harness, icd_catalog)
    before = await note_detail(harness, practice, note_id)
    assert (before["note"]["lane"], before["note"]["lane_reason"]) == ("compliance", "audit_risk")
    compliance = await compliance_member(harness, practice)

    assert (await send_back(harness, compliance, note_id)).status_code == 200

    detail = await note_detail(harness, practice, note_id)
    assert (detail["note"]["lane"], detail["note"]["lane_reason"], detail["note"]["headline"]) == (
        "coder",
        "returned",
        "Returned",
    )
    ready = await harness.client.get("/api/notes", headers=practice.admin, params={"lane": "approve"})
    assert ready.json()["items"] == []
    bulk = await harness.client.post("/api/notes/approve", headers=practice.admin, json={"note_ids": [note_id]})
    assert (bulk.status_code, bulk.json()["message"]) == (409, RETURNED_ALONE)
    if any(item["decide_again"] for item in detail["findings"]):
        assert (await decide_again(harness, practice, detail)).status_code == 200
    assert (await approve(harness, practice, note_id)).status_code == 200


async def test_the_return_tells_the_coder_who_flagged_the_note_with_the_reason_only(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"], secret_box=practice.secrets)
    await flag(harness, coder, note_id)
    compliance = await compliance_member(harness, practice)

    assert (await send_back(harness, compliance, note_id)).status_code == 200

    assert entries(await inbox_of(harness, coder)) == [
        ("compliance_returned", "Jordan Diaz", note_id, {"reason": "level_not_supported"})
    ]
    assert entries(await inbox_of(harness, practice.admin)) == []
    [item] = [row for row in await stored_items() if row.kind == "compliance_returned"]
    assert item.payload == {"reason": "level_not_supported"}


async def test_a_stored_return_cannot_be_changed_or_removed(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await flag(harness, practice.admin, note_id)
    await send_back(harness, await compliance_member(harness, practice), note_id)
    for statement in ("UPDATE note_returns SET reason = 'other', note = 'changed'", "DELETE FROM note_returns"):
        async with SessionFactory() as db:
            with pytest.raises(DBAPIError, match="refused on"):
                await db.execute(text(statement))
