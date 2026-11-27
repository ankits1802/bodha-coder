import json

from tests.api.review_helpers import access_rows
from tests.batches import add_provider, lines_pdf
from tests.builders import practice_with_provider, upload_note
from tests.fakes import NOTE_TEXT, text_pdf

VARGA_PAGE = (
    "Patient: REYES, MARISOL DOB: 03/14/1959 Date of service: 11/24/2026 Place of service: 11 "
    "Rendering provider: Elena Varga MD NPI 1234567893"
)
HADDAD_LINES = ["Progress note", "Seen by Omar Haddad, DO", "Visit date: November 23, 2026", "Patient name: Jonah Pike"]
SURNAME_ONLY = "Follow up visit. Dr. Varga reviewed the labs."
DISAGREEING = "DOS: 11/20/2026 Elena Varga, MD"


def pdf_part(name: str, content: bytes) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, content, "application/pdf"))


async def preview(harness, practice, parts):
    response = await harness.client.post("/api/uploads/preview", headers=practice.admin, files=parts)
    assert response.status_code == 200, response.text
    return response.json()


def matched(row: dict) -> tuple:
    return (row["provider_id"], row["service_date"], row["place_code"], row["patient_name"], row["check"])


async def test_page_one_names_provider_date_place_and_patient_with_a_confidence(harness):
    practice = await practice_with_provider(harness)
    haddad = await add_provider(harness, practice, name="Omar Haddad", specialty=None)
    await upload_note(harness, practice)
    parts = [
        pdf_part("visit-001.pdf", text_pdf(VARGA_PAGE)),
        pdf_part("visit-002.pdf", lines_pdf(HADDAD_LINES)),
        pdf_part("2026-11-22 - GRAY ANNA - 99213 - Visit.pdf", text_pdf(SURNAME_ONLY)),
        pdf_part("scan-17.pdf", text_pdf("Scanned page")),
        pdf_part("2026-11-21 - PIKE JONAH - 99214 - Visit.pdf", text_pdf(DISAGREEING)),
        pdf_part("copy.pdf", text_pdf(NOTE_TEXT)),
    ]

    rows = await preview(harness, practice, parts)

    assert [matched(row) for row in rows] == [
        (practice.provider_id, "2026-11-24", "11", "Marisol Reyes", False),
        (haddad, "2026-11-23", "11", "Jonah Pike", False),
        (practice.provider_id, "2026-11-22", "11", "Gray Anna", True),
        (None, None, None, None, True),
        (practice.provider_id, "2026-11-20", "11", "Pike Jonah", True),
        (None, None, None, None, True),
    ]
    assert rows[0]["confidence"] == {"provider": 0.99, "service_date": 0.95, "place": 0.95, "patient": 0.9}
    assert [(row["overall"], row["cpt"]) for row in rows[:3]] == [(0.95, None), (0.8, None), (0.6, "99213")]
    assert [row["duplicate"] for row in rows] == [False, False, False, False, False, True]


async def test_previewing_reads_no_model_and_is_written_to_the_access_log(harness):
    practice = await practice_with_provider(harness)

    await preview(harness, practice, [pdf_part("visit-001.pdf", text_pdf(VARGA_PAGE))])

    previewed = [row for row in await access_rows(harness, practice) if row["action"] == "previewed uploads"]
    assert [row["detail"] for row in previewed] == ["1 files"]


async def test_a_preview_refuses_a_file_that_is_not_a_pdf(harness):
    practice = await practice_with_provider(harness)
    refused = await harness.client.post(
        "/api/uploads/preview", headers=practice.admin, files=[pdf_part("notes.txt", b"plain text")]
    )
    assert (refused.status_code, refused.json()["message"]) == (422, "notes.txt is not a PDF")


def detail(provider_id: str, day: str, place: str, billed: str) -> dict:
    return {"billed": billed, "visit_type": None, "provider_id": provider_id, "service_date": day, "place_code": place}


async def test_the_server_groups_files_into_one_batch_per_provider_date_and_place(harness):
    practice = await practice_with_provider(harness)
    haddad = await add_provider(harness, practice, name="Omar Haddad", specialty=None)
    details = [
        detail(practice.provider_id, "2026-11-24", "11", "99214"),
        detail(haddad, "2026-11-23", "31", "99309"),
        detail(practice.provider_id, "2026-11-24", "11", "99213"),
    ]
    files = [pdf_part(f"visit-{n}.pdf", text_pdf(f"{NOTE_TEXT} visit {n}")) for n in range(3)]

    uploaded = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={"visit_type": "Established patient", "details": json.dumps(details)},
        files=files,
    )

    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert (len(body["batch_ids"]), body["batch_id"], body["accepted"]) == (
        2,
        body["batch_ids"][0],
        ["visit-0.pdf", "visit-2.pdf", "visit-1.pdf"],
    )
    history = (await harness.client.get("/api/batches", headers=practice.admin)).json()["items"]
    assert sorted(
        (row["provider_name"], row["service_date"], row["place_code"], row["counts"]["queued"]) for row in history
    ) == [
        ("Elena Varga", "2026-11-24", "11", 2),
        ("Omar Haddad", "2026-11-23", "31", 1),
    ]


async def test_a_file_without_a_provider_date_or_place_stops_the_whole_upload(harness):
    practice = await practice_with_provider(harness)
    details = [detail(practice.provider_id, "2026-11-24", "11", "99214"), {"billed": None, "visit_type": None}]
    files = [pdf_part("good.pdf", text_pdf("good")), pdf_part("scan.pdf", text_pdf("scan"))]

    refused = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={"visit_type": "Established patient", "details": json.dumps(details)},
        files=files,
    )

    assert refused.status_code == 422
    assert refused.json()["message"] == "scan.pdf: choose the provider, date of service and place of service"
    assert (await harness.client.get("/api/batches", headers=practice.admin)).json()["total"] == 0


async def test_the_same_file_is_still_refused_as_a_duplicate_across_batches(harness):
    practice = await practice_with_provider(harness)
    first = await upload_note(harness, practice)
    assert first.status_code == 200, first.text
    again = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "visit_type": "Established patient",
            "details": json.dumps([detail(practice.provider_id, "2026-11-20", "11", "99214")]),
        },
        files=[pdf_part("renamed.pdf", text_pdf(NOTE_TEXT))],
    )
    assert again.status_code == 200, again.text
    assert (again.json()["accepted"], again.json()["duplicates"]) == ([], ["renamed.pdf"])
