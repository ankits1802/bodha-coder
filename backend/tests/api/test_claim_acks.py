import pytest
from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import ClaimAck, ClaimAckFile
from tests.acknowledgments import ACCEPTED_CLAIM, REJECTED_CLAIM, ack_277, ack_999
from tests.api.claim_helpers import access_entries, billing_row, ok, only_submission, poll, ready_claim

pytestmark = pytest.mark.usefixtures("clearinghouse_key")
SEND = "/api/billing/claim-submissions"
UPLOAD = "/api/billing/acknowledgments"


async def _sent(harness, icd_catalog):
    practice, note_id = await ready_claim(harness, icd_catalog)
    ok(await harness.client.post(SEND, headers=practice.admin, json={}))
    return practice, note_id, await only_submission(practice)


async def test_a_rejected_999_returns_the_claim_to_ready_and_tells_the_billers(harness, icd_catalog):
    practice, note_id, _ = await _sent(harness, icd_catalog)
    harness.link.inbound["SUB123_999_0001.txt"] = ack_999(1, accepted=False)

    assert await poll(harness) == 1

    row = await billing_row(harness, practice, note_id)
    assert (row["claim"]["status"], row["exported_at"], row["claim"]["missing"]) == ("rejected", None, [])
    assert [reason["text"] for reason in row["claim"]["reasons"]] == [
        "segment NM1 16 (loop 2010BA): segment has data element errors",
        "element 9 of segment NM1 16 (loop 2010BA): required data element missing",
        "transaction: one or more segments in error",
    ]
    inbox = ok(await harness.client.get("/api/inbox", headers=practice.admin))
    rejected = [(item["note_id"], item["payload"]) for item in inbox["items"] if item["kind"] == "claim_rejected"]
    assert rejected == [(note_id, {"source": "999", "claims": 1})]
    actions = [(entry.action, entry.note_id) for entry in await access_entries(practice)]
    assert ("claim rejected by the clearinghouse", note_id) in actions
    assert ("received a clearinghouse response", None) in actions
    assert await poll(harness) == 0
    assert harness.link.downloads == ["SUB123_999_0001.txt"]


async def test_an_accepted_277ca_marks_the_claim_accepted_with_the_payer_claim_number(harness, icd_catalog):
    practice, note_id, submission = await _sent(harness, icd_catalog)
    harness.link.inbound["277ca.txt"] = ack_277(submission.batch_ref, [(note_id[:20].upper(), ACCEPTED_CLAIM)])

    assert await poll(harness) == 1

    row = await billing_row(harness, practice, note_id, show="exported")
    assert row["claim"]["status"] == "accepted"
    assert row["claim"]["reasons"] == [{"code": "A2:20:PR", "text": "accepted into adjudication (status 20)"}]
    async with SessionFactory() as db:
        ack = await db.scalar(select(ClaimAck).where(ClaimAck.level == "claim"))
    assert (ack.note_id, ack.submission_id, ack.payer_claim_number, ack.outcome) == (
        note_id,
        submission.id,
        "PAYER123",
        "accepted",
    )


async def test_a_277ca_rejection_names_its_reason_and_the_claim_can_be_sent_again(harness, icd_catalog):
    practice, note_id, submission = await _sent(harness, icd_catalog)
    harness.link.inbound["277ca.txt"] = ack_277(submission.batch_ref, [(note_id[:20].upper(), REJECTED_CLAIM)])

    assert await poll(harness) == 1

    row = await billing_row(harness, practice, note_id)
    assert row["claim"]["status"] == "rejected"
    assert row["claim"]["reasons"] == [
        {"code": "A7:562:85", "text": "rejected for invalid information (status 562): billing provider npi invalid"}
    ]
    ok(await harness.client.post(SEND, headers=practice.admin, json={"note_ids": [note_id]}))
    assert [name for _, name, _ in harness.link.uploads] == ["bodha-837p-000000001.txt", "bodha-837p-000000002.txt"]
    assert (await billing_row(harness, practice, note_id, show="exported"))["claim"]["status"] == "sent"


async def test_a_biller_can_upload_a_response_by_hand_once(harness, icd_catalog):
    practice, note_id, _ = await _sent(harness, icd_catalog)
    files = {"file": ("999.txt", ack_999(1, accepted=True), "text/plain")}

    uploaded = ok(await harness.client.post(UPLOAD, headers=practice.admin, files=files))

    assert uploaded == {"kind": "999", "accepted": 1, "rejected": 0, "pending": 0, "unlinked": 0}
    again = ok(await harness.client.post(UPLOAD, headers=practice.admin, files=files))
    assert again == {"kind": "duplicate", "accepted": 0, "rejected": 0, "pending": 0, "unlinked": 0}
    refused = await harness.client.post(
        UPLOAD, headers=practice.admin, files={"file": ("a.txt", b"hello", "text/plain")}
    )
    assert refused.status_code == 422
    assert (await billing_row(harness, practice, note_id, show="exported"))["claim"]["status"] == "sent"
    actions = [entry.action for entry in await access_entries(practice)]
    assert actions.count("uploaded a clearinghouse response") == 2


async def test_a_file_that_is_not_an_acknowledgment_is_kept_but_never_read_again(harness, icd_catalog):
    practice, _, _ = await _sent(harness, icd_catalog)
    harness.link.inbound["weekly-report.txt"] = b"Weekly summary of files received"

    assert await poll(harness) == 1

    async with SessionFactory() as db:
        files = list(await db.scalars(select(ClaimAckFile)))
    assert [(item.kind, item.source, item.practice_id) for item in files] == [("unreadable", "sftp", practice.id)]
    assert harness.store.objects[files[0].file_key] == b"Weekly summary of files received"
    assert await poll(harness) == 0


async def test_a_response_for_an_unknown_file_is_kept_unlinked(harness, icd_catalog):
    practice, note_id, _ = await _sent(harness, icd_catalog)
    harness.link.inbound["999.txt"] = ack_999(99, accepted=False)

    assert await poll(harness) == 1

    async with SessionFactory() as db:
        ack = await db.scalar(select(ClaimAck))
    assert (ack.outcome, ack.submission_id) == ("rejected", None)
    assert (await billing_row(harness, practice, note_id, show="exported"))["claim"]["status"] == "sent"
