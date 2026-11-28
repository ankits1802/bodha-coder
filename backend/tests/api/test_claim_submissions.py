import hashlib

import pytest

from app.services.claim_837_check import check_837p
from tests.api.claim_helpers import (
    PORTAL,
    SFTP,
    access_entries,
    approved_note,
    billing_row,
    ok,
    only_submission,
    ready_claim,
)
from tests.builders import invite_member, sign_in

pytestmark = pytest.mark.usefixtures("clearinghouse_key")
SEND = "/api/billing/claim-submissions"
CLAIM_FILE = "/api/billing/claim-file"
EVERYTHING_MISSING = [
    "connection",
    "practice.legal_name",
    "practice.tax_id",
    "practice.address",
    "practice.city",
    "practice.state",
    "practice.zip",
    "practice.phone",
    "practice.billing_contact",
    "payer",
    "details",
    "charge:99214",
    "charge:96127",
]


def _expected(reference: str) -> tuple[str, ...]:
    return (
        "ST*837*0001*005010X222A1",
        "NM1*41*2*LAKESIDE FAMILY MEDICINE*****46*SUB123",
        "PER*IC*DANA BILLER*TE*5555551234",
        "NM1*40*2*OFFICE ALLY*****46*OFFALLY",
        "PRV*BI*PXC*207Q00000X",
        "NM1*85*2*LAKESIDE FAMILY MEDICINE*****XX*1245319599",
        "N3*123 MAIN ST*SUITE 200",
        "N4*SPRINGFIELD*IL*627011234",
        "REF*EI*123456789",
        "SBR*P*18*******MB",
        "NM1*IL*1*REYES*MARISOL****MI*1EG4-TE5-MK72",
        "DMG*D8*19590312*F",
        "NM1*PR*2*MEDICARE PART B*****PI*MCRB",
        f"CLM*{reference}*170***11:B:1*Y*A*Y*Y",
        "HI*ABK:E1165*ABF:N1830*ABF:I129*ABF:R202",
        "NM1*82*1*VARGA*ELENA****XX*1234567893",
        "PRV*PE*PXC*207R00000X",
        "SV1*HC:99214*150*UN*1***1:2:3:4",
        "SV1*HC:96127*20*UN*2***1:2:3:4",
        "DTP*472*D8*20261125",
    )


def _segments(data: bytes) -> list[str]:
    text = data.decode("ascii")
    check_837p(text)
    return text[:-1].split("~")


async def test_a_ready_claim_goes_to_the_clearinghouse_as_a_checked_837p_file(harness, icd_catalog):
    practice, note_id = await ready_claim(harness, icd_catalog)
    assert (await billing_row(harness, practice, note_id))["claim"] == {
        "status": "ready",
        "at": None,
        "reasons": [],
        "missing": [],
    }

    sent = ok(await harness.client.post(SEND, headers=practice.admin, json={}))

    submission = await only_submission(practice)
    assert sent == {"id": submission.id, "claims": 1, "outcome": "delivered"}
    ((folder, name, data),) = harness.link.uploads
    assert (folder, name) == ("/outbound", "bodha-837p-000000001.txt")
    segments = _segments(data)
    assert segments[0].startswith("ISA*00*          *00*          *ZZ*SUB123         *ZZ*OFFALLY        *")
    assert segments[0].endswith("*^*00501*000000001*0*T*:")
    for expected in _expected(note_id[:20].upper()):
        assert expected in segments
    assert any(segment.startswith(f"BHT*0019*00*{submission.batch_ref}*") for segment in segments)
    assert harness.store.objects[f"practices/{practice.id}/claim-files/{submission.id}.x12"] == data
    assert submission.file_sha256 == hashlib.sha256(data).hexdigest()
    assert harness.link.targets[-1].password == SFTP["password"]
    assert await billing_row(harness, practice, note_id) is None
    exported = await billing_row(harness, practice, note_id, show="exported")
    assert exported["claim"]["status"] == "sent" and exported["exported_at"] is not None


async def test_sending_is_in_the_access_log_without_patient_details(harness, icd_catalog):
    practice, _ = await ready_claim(harness, icd_catalog)
    ok(await harness.client.post(SEND, headers=practice.admin, json={}))

    entries = await access_entries(practice)

    sent = [entry.detail for entry in entries if entry.action == "sent claims to the clearinghouse"]
    assert len(sent) == 1 and sent[0].startswith("1 claims · file 000000001 · test · sha256 ")
    claim_actions = {"sent claims to the clearinghouse", "saved claim details", "saved clearinghouse connection"}
    details = " ".join(entry.detail or "" for entry in entries if entry.action in claim_actions)
    assert "Reyes" not in details and "Marisol" not in details and "1EG4" not in details


async def test_a_failed_delivery_stays_ready_and_the_resend_takes_the_next_control_number(harness, icd_catalog):
    practice, note_id = await ready_claim(harness, icd_catalog)
    harness.link.refusal = "the connection to the clearinghouse failed"

    failed = await harness.client.post(SEND, headers=practice.admin, json={})

    assert failed.status_code == 503
    assert failed.json()["message"] == "the connection to the clearinghouse failed"
    row = await billing_row(harness, practice, note_id)
    assert (row["claim"]["status"], row["exported_at"]) == ("failed", None)
    assert row["claim"]["reasons"] == [{"code": "delivery", "text": "the connection to the clearinghouse failed"}]
    harness.link.refusal = None
    ok(await harness.client.post(SEND, headers=practice.admin, json={"note_ids": [note_id]}))
    assert [name for _, name, _ in harness.link.uploads] == ["bodha-837p-000000002.txt"]
    assert _segments(harness.link.uploads[0][2])[0].endswith("*^*00501*000000002*0*T*:")


async def test_a_portal_practice_downloads_the_file_and_can_download_it_again(harness, icd_catalog):
    practice, note_id = await ready_claim(harness, icd_catalog, connection=PORTAL)

    response = await harness.client.post(CLAIM_FILE, headers=practice.admin, json={})

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/edi-x12")
    assert response.headers["content-disposition"] == 'attachment; filename="bodha-837p-000000001.txt"'
    isa = _segments(response.content)[0]
    assert "*ZZ*AV123          *ZZ*030240928      *" in isa and isa.endswith("*00501*000000001*0*P*:")
    page = ok(await harness.client.get(SEND, headers=practice.admin))
    assert page["total"] == 1
    record = page["items"][0]
    assert (record["outcome"], record["delivery"], record["claims"], record["total_cents"]) == (
        "downloaded",
        "download",
        1,
        17000,
    )
    again = await harness.client.get(f"{SEND}/{record['id']}/file", headers=practice.admin)
    assert again.content == response.content
    refused = await harness.client.post(SEND, headers=practice.admin, json={})
    assert refused.status_code == 409
    assert (await billing_row(harness, practice, note_id, show="exported"))["claim"]["status"] == "sent"


async def test_missing_information_is_listed_per_claim_and_nothing_unready_is_sent(harness, icd_catalog):
    practice, note_id = await approved_note(harness, icd_catalog)

    row = await billing_row(harness, practice, note_id)

    assert (row["claim"]["status"], row["claim"]["missing"]) == ("missing", EVERYTHING_MISSING)
    listed = ok(await harness.client.get("/api/billing", headers=practice.admin))
    assert listed["clearinghouse"] is None
    no_connection = await harness.client.post(CLAIM_FILE, headers=practice.admin, json={})
    assert (no_connection.status_code, no_connection.json()["message"]) == (
        409,
        "set up the clearinghouse in Settings first",
    )
    ok(await harness.client.put("/api/practice/clearinghouse", headers=practice.admin, json=PORTAL))
    nothing = await harness.client.post(CLAIM_FILE, headers=practice.admin, json={})
    assert (nothing.status_code, nothing.json()["message"]) == (422, "no claims are ready to send")
    named = await harness.client.post(CLAIM_FILE, headers=practice.admin, json={"note_ids": [note_id]})
    assert named.status_code == 422
    assert (
        named.json()["message"]
        == "some of the chosen claims are missing information or are already with the clearinghouse"
    )


async def test_the_claim_lines_export_still_works_and_takes_the_claim_off_the_send_list(harness, icd_catalog):
    practice, note_id = await ready_claim(harness, icd_catalog)

    exported = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"format": "csv"})

    assert exported.status_code == 200 and exported.headers["content-type"].startswith("text/csv")
    assert (await billing_row(harness, practice, note_id, show="exported"))["claim"] is None
    nothing = await harness.client.post(SEND, headers=practice.admin, json={})
    assert (nothing.status_code, nothing.json()["message"]) == (422, "no claims are ready to send")
    assert harness.link.uploads == []


async def test_billers_send_claims_but_only_admins_manage_the_connection(harness, icd_catalog):
    practice, _ = await ready_claim(harness, icd_catalog)
    await invite_member(harness, practice, name="Bea Biller", email="biller@lakeside.example.com", role="biller")
    await invite_member(harness, practice, name="Cole Coder", email="coder@lakeside.example.com", role="coder")
    biller = await sign_in(harness.client, "biller@lakeside.example.com", secret_box=practice.secrets)
    coder = await sign_in(harness.client, "coder@lakeside.example.com", secret_box=practice.secrets)

    assert (await harness.client.put("/api/practice/clearinghouse", headers=biller, json=SFTP)).status_code == 403
    assert (await harness.client.get("/api/practice/clearinghouse", headers=biller)).status_code == 403
    assert (await harness.client.post(SEND, headers=coder, json={})).status_code == 403
    ok(await harness.client.post(SEND, headers=biller, json={}))
    assert len(harness.link.uploads) == 1
