from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import Note
from tests.builders import invite_member, reviewed_note, sign_in

ELENA = {
    "name": "Elena Varga",
    "credential": "MD",
    "specialty": "Internal medicine",
    "npi": "1234567893",
    "place_code": "11",
    "email": "varga@clinic.example.com",
}
GROUP_BILLING = {"taxonomy_code": "207R00000X", "bills_under": "group", "group_npi": "1245319599"}
CSV_HEADER = (
    "note_id,patient,service_date,place_of_service,rendering_npi,rendering_taxonomy,billing_npi,line,procedure,"
    "modifier_1,modifier_2,modifier_3,modifier_4,units,diagnosis_pointers,diagnosis_a,diagnosis_b,diagnosis_c,"
    "diagnosis_d,diagnosis_e,diagnosis_f,diagnosis_g,diagnosis_h,diagnosis_i,diagnosis_j,diagnosis_k,diagnosis_l"
)


async def _bill(harness, practice, note_id: str, codes: str) -> None:
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes", headers=practice.admin, json={"codes": codes}
    )
    assert edited.status_code == 200, edited.text


async def _checks(harness, practice, note_id: str) -> dict:
    response = await harness.client.get(f"/api/notes/{note_id}/claim-checks", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()


async def test_claim_checks_list_ncci_pairs_and_units_for_the_current_claim(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _bill(harness, practice, note_id, "99215, 20610, 96127x5, I10, E11.9, N18.30")

    checks = await _checks(harness, practice, note_id)

    assert checks == {
        "ncci": {"quarter": "2026Q4", "covers": True},
        "edits": [
            {"kind": "ptp", "column1": "20610", "column2": "99214", "modifier_allowed": True, "bypassed_by": None},
            {"kind": "mue", "code": "96127", "units": 5, "limit": 4, "mai": 3},
        ],
        "payer": None,
        "payer_flags": [],
    }


async def test_modifier_25_bypasses_the_pair_and_the_medicare_payer_flags_g2211(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _bill(harness, practice, note_id, "99215-25, G2211, 20610, I10, E11.9, N18.30")
    payer = await harness.client.post(
        "/api/practice/payers",
        headers=practice.admin,
        json={"name": "Medicare Part B", "payer_id": "MCRB", "plan_type": "medicare"},
    )
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == note_id).values(payer=payer.json()["id"]))
        await db.commit()

    checks = await _checks(harness, practice, note_id)

    assert checks["edits"] == [
        {"kind": "ptp", "column1": "20610", "column2": "99214", "modifier_allowed": True, "bypassed_by": "25"}
    ]
    assert checks["payer"] == {"name": "Medicare Part B", "plan_type": "medicare"}
    assert checks["payer_flags"] == [
        {"rule": "complexity_with_25", "severity": "denial", "codes": ["99214-25", "G2211"]}
    ]


async def test_claim_checks_belong_to_the_practice(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    missing = await harness.client.get("/api/notes/not-a-note/claim-checks", headers=practice.admin)
    assert missing.status_code == 404


async def _approved_with_group_billing(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _bill(harness, practice, note_id, "99215, 96127x2, I10, E11.9, N18.30")
    provider = await harness.client.put(
        f"/api/providers/{practice.provider_id}", headers=practice.admin, json={**ELENA, "details": GROUP_BILLING}
    )
    assert provider.status_code == 204, provider.text
    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.status_code == 200, approved.text
    patient = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["note"]["patient_name"]
    return practice, note_id, patient


async def test_claim_lines_point_every_line_to_the_first_four_diagnoses(harness, icd_catalog):
    practice, note_id, patient = await _approved_with_group_billing(harness, icd_catalog)

    response = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"format": "json"})

    assert response.status_code == 200, response.text
    pointers = ["A", "B", "C", "D"]
    assert response.json() == {
        "claims": [
            {
                "note_id": note_id,
                "patient_name": patient,
                "service_date": "2026-11-25",
                "place_of_service": "11",
                "rendering_npi": "1234567893",
                "rendering_taxonomy": "207R00000X",
                "billing_npi": "1245319599",
                "diagnoses": [
                    {"pointer": "A", "code": "E1165"},
                    {"pointer": "B", "code": "N1830"},
                    {"pointer": "C", "code": "I129"},
                    {"pointer": "D", "code": "R202"},
                ],
                "lines": [
                    {"line": 1, "procedure": "99214", "modifiers": [], "units": 1, "pointers": pointers},
                    {"line": 2, "procedure": "96127", "modifiers": [], "units": 2, "pointers": pointers},
                ],
            }
        ]
    }


async def test_claim_lines_as_csv_leave_the_visit_ready_to_export(harness, icd_catalog):
    practice, note_id, patient = await _approved_with_group_billing(harness, icd_catalog)

    response = await harness.client.post(
        "/api/billing/claim-lines", headers=practice.admin, json={"note_ids": [note_id], "format": "csv"}
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    header, first, second = response.text.splitlines()
    shared = f"{note_id},{patient or ''},2026-11-25,11,1234567893,207R00000X,1245319599"
    diagnoses = "E1165,N1830,I129,R202" + "," * 8
    assert header == CSV_HEADER
    assert first == f"{shared},1,99214,,,,,1,ABCD,{diagnoses}"
    assert second == f"{shared},2,96127,,,,,2,ABCD,{diagnoses}"
    billing = (await harness.client.get("/api/billing", headers=practice.admin)).json()
    assert (billing["summary"]["ready"], billing["items"][0]["exported_at"]) == (1, None)


async def test_claim_lines_need_an_approved_visit_and_a_biller(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    nothing = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={})
    assert nothing.status_code == 422
    assert nothing.json()["message"] == "no approved visits are waiting for export"

    await invite_member(harness, practice, name="Cole Coder", email="coder@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "coder@lakeside.example.com", secret_box=practice.secrets)
    refused = await harness.client.post("/api/billing/claim-lines", headers=coder, json={"note_ids": [note_id]})
    assert refused.status_code == 403


CLAIM_DIAGNOSES = ["E11.65", "N18.30", "I12.9", "R20.2"]


async def _link(harness, headers, note_id: str, lines: list[dict]):
    return await harness.client.put(f"/api/notes/{note_id}/pointers", headers=headers, json={"lines": lines})


async def _billed_with_screening(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _bill(harness, practice, note_id, "99215, 96127x2, I10, E11.9, N18.30")
    return practice, note_id


async def test_lines_point_to_the_first_four_diagnoses_until_a_coder_links_them(harness, icd_catalog):
    practice, note_id = await _billed_with_screening(harness, icd_catalog)

    shown = await harness.client.get(f"/api/notes/{note_id}/pointers", headers=practice.admin)

    assert shown.status_code == 200, shown.text
    assert shown.json() == {
        "diagnoses": [{"code": code, "letter": letter} for code, letter in zip(CLAIM_DIAGNOSES, "ABCD", strict=True)],
        "lines": [
            {"code": "99214", "label": "99214", "pointers": CLAIM_DIAGNOSES, "stored": False},
            {"code": "96127", "label": "96127 ×2", "pointers": CLAIM_DIAGNOSES, "stored": False},
        ],
    }


async def test_linked_diagnoses_reach_the_final_claim_and_the_claim_lines(harness, icd_catalog):
    practice, note_id = await _billed_with_screening(harness, icd_catalog)

    linked = await _link(harness, practice.admin, note_id, [{"code": "96127", "pointers": ["R20.2", "e1165"]}])

    assert linked.status_code == 200, linked.text
    assert linked.json()["lines"][1] == {
        "code": "96127",
        "label": "96127 ×2",
        "pointers": ["R20.2", "E11.65"],
        "stored": True,
    }
    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.status_code == 200, approved.text
    history = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["history"]
    final = next(item for item in history["code_sets"] if item["kind"] == "final")
    assert final["codes"][:2] == [
        {"code": "99214", "type": "CPT", "modifiers": [], "units": 1},
        {"code": "96127", "type": "CPT", "modifiers": [], "units": 2, "pointers": ["R20.2", "E11.65"]},
    ]
    exported = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={})
    assert [(line["procedure"], line["pointers"]) for line in exported.json()["claims"][0]["lines"]] == [
        ("99214", ["A", "B", "C", "D"]),
        ("96127", ["D", "A"]),
    ]


async def test_pointers_name_diagnoses_and_lines_of_the_claim(harness, icd_catalog):
    practice, note_id = await _billed_with_screening(harness, icd_catalog)

    replaced = await _link(harness, practice.admin, note_id, [{"code": "96127", "pointers": ["I10"]}])
    billed_level = await _link(harness, practice.admin, note_id, [{"code": "99215", "pointers": ["E11.65"]}])
    twice = await _link(
        harness,
        practice.admin,
        note_id,
        [{"code": "96127", "pointers": ["E11.65"]}, {"code": "96127", "pointers": ["R20.2"]}],
    )
    five = await _link(harness, practice.admin, note_id, [{"code": "99214", "pointers": [*CLAIM_DIAGNOSES, "I10"]}])

    assert (replaced.status_code, replaced.json()["message"]) == (422, "I10 is not a diagnosis on the claim")
    assert (billed_level.status_code, billed_level.json()["message"]) == (
        422,
        "99215 is not a procedure line of the claim",
    )
    assert (twice.status_code, twice.json()["message"]) == (422, "96127 is listed twice")
    assert five.status_code == 422


async def test_an_empty_choice_returns_a_line_to_the_default(harness, icd_catalog):
    practice, note_id = await _billed_with_screening(harness, icd_catalog)
    await _link(harness, practice.admin, note_id, [{"code": "99214", "pointers": ["I12.9"]}])

    reset = await _link(harness, practice.admin, note_id, [{"code": "99214", "pointers": []}])

    assert reset.json()["lines"][0] == {"code": "99214", "label": "99214", "pointers": CLAIM_DIAGNOSES, "stored": False}


async def test_only_deciders_link_diagnoses_and_only_while_the_note_is_open(harness, icd_catalog):
    practice, note_id = await _billed_with_screening(harness, icd_catalog)
    await invite_member(harness, practice, name="Bea Biller", email="biller@lakeside.example.com", role="biller")
    biller = await sign_in(harness.client, "biller@lakeside.example.com", secret_box=practice.secrets)

    refused = await _link(harness, biller, note_id, [{"code": "99214", "pointers": ["I12.9"]}])
    shown = await harness.client.get(f"/api/notes/{note_id}/pointers", headers=biller)
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    closed = await _link(harness, practice.admin, note_id, [{"code": "99214", "pointers": ["I12.9"]}])

    assert (refused.status_code, shown.status_code) == (403, 200)
    assert (closed.status_code, closed.json()["message"]) == (409, "this note is not open for review")
