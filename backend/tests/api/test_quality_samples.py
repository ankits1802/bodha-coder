from datetime import date

import pytest
from sqlalchemy import select

from app.codes.billing_codes import Code
from app.core.db import SessionFactory
from app.models import AuditRun, AuditSample
from tests.api.quality_helpers import CODER_EMAIL, SERVICE_DAY, approved_note, note_of_item, read_note, user_id
from tests.builders import DOCUMENTED, invite_member, practice_with_provider, sign_in

PERIOD = {"start": SERVICE_DAY, "end": SERVICE_DAY}
ANSWERS = {
    "first": {"em": "99214", "icd": ["E11.65", "I12.9", "N18.30"], "modifiers": []},
    "second": {"em": "99215", "icd": ["E11.65", "I10", "I12.9", "N18.30", "R20.2"], "modifiers": ["25"]},
}


def assert_rate(found: dict, successes: int, trials: int, low: float, high: float) -> None:
    assert (found["successes"], found["trials"]) == (successes, trials)
    assert found["low"] == pytest.approx(low, abs=1e-6)
    assert found["high"] == pytest.approx(high, abs=1e-6)


async def audit_setup(harness, icd_catalog, *, purpose: str = "audit"):
    practice = await practice_with_provider(harness)
    first = await approved_note(harness, practice, icd_catalog, 1)
    second = await approved_note(harness, practice, icd_catalog, 2, {"em": "keep", "dx:I10": "keep"})
    coder_id = await invite_member(harness, practice, name="Coder One", email=CODER_EMAIL, role="coder")
    coder = await sign_in(harness.client, CODER_EMAIL, secret_box=practice.secrets)
    if purpose == "audit":
        body = {"scope": "practice", **PERIOD, "reviewer_ids": [coder_id]}
        started = await harness.client.post("/api/quality/samples", headers=practice.admin, json=body)
    else:
        body = {"trainee_id": coder_id, **PERIOD, "size": 5}
        started = await harness.client.post("/api/training/sets", headers=practice.admin, json=body)
    assert started.status_code == 200, started.text
    return practice, coder, started.json()["id"], {first: "first", second: "second"}


def reference_labels(item: AuditSample, side: str) -> list[str]:
    return sorted(Code.from_json(code).label() for code in item.result["reference"][side])


async def stored_run(run_id: str) -> tuple[AuditRun, list[str | None]]:
    async with SessionFactory() as db:
        run = await db.get_one(AuditRun, run_id)
        items = await db.scalars(select(AuditSample.run_id).where(AuditSample.practice_id == run.practice_id))
        return run, list(items.all())


async def code_next(harness, coder, sample_id, notes) -> dict:
    step = (await harness.client.get(f"/api/blind-review/{sample_id}/next", headers=coder)).json()
    if step["item"] is None:
        return step
    answer = ANSWERS[notes[await note_of_item(step["item"]["id"])]]
    answered = await harness.client.post(
        f"/api/blind-review/items/{step['item']['id']}/answer", headers=coder, json=answer
    )
    assert answered.status_code == 200, answered.text
    return step


async def test_a_blind_audit_is_one_run_that_closes_when_every_note_is_coded(harness, icd_catalog):
    practice, coder, run_id, notes = await audit_setup(harness, icd_catalog)
    run, item_runs = await stored_run(run_id)
    admin_id = await user_id("admin@lakeside.example.com")
    day = date.fromisoformat(SERVICE_DAY)
    assert (run.purpose, run.scope, run.requested, run.created_by) == ("audit", "practice", 40, admin_id)
    assert (run.period_start, run.period_end, run.status, item_runs) == (day, day, "open", [run_id, run_id])

    await code_next(harness, coder, run_id, notes)
    assert (await stored_run(run_id))[0].status == "open"
    await code_next(harness, coder, run_id, notes)
    assert (await stored_run(run_id))[0].status == "done"
    listed = (await harness.client.get("/api/quality/samples", headers=practice.admin)).json()["items"]
    assert [(row["id"], row["status"], row["started_by"]) for row in listed] == [(run_id, "done", "Practice Admin")]


async def test_a_blind_audit_scores_visits_with_wilson_and_diagnoses_with_a_note_bootstrap(harness, icd_catalog):
    practice, coder, sample_id, notes = await audit_setup(harness, icd_catalog)
    for _ in range(2):
        await code_next(harness, coder, sample_id, notes)
    finished = await code_next(harness, coder, sample_id, notes)
    assert (finished["item"], finished["sample"]["done"], finished["sample"]["total"]) == (None, 2, 2)

    results = (await harness.client.get(f"/api/quality/samples/{sample_id}", headers=practice.admin)).json()
    bodha, claim = results["summary"]["bodha"], results["summary"]["claim"]
    assert_rate(bodha["em"], 1, 2, 0.094531, 0.905469)
    assert_rate(bodha["em_lower"], 1, 2, 0.094531, 0.905469)
    assert_rate(bodha["em_higher"], 0, 2, 0.0, 0.65762)
    assert_rate(bodha["icd_precision"], 7, 8, 0.75, 1.0)
    assert_rate(bodha["icd_recall"], 7, 8, 0.8, 1.0)
    assert bodha["icd_f1"] == pytest.approx(0.875)
    assert_rate(bodha["icd_exact"], 0, 2, 0.0, 0.65762)
    assert_rate(bodha["modifiers"], 1, 2, 0.094531, 0.905469)
    assert_rate(claim["em"], 2, 2, 0.34238, 1.0)
    assert_rate(claim["icd_precision"], 8, 9, 0.75, 1.0)
    assert_rate(claim["icd_recall"], 8, 8, 1.0, 1.0)
    assert claim["icd_f1"] == pytest.approx(16 / 17)
    assert_rate(claim["icd_exact"], 1, 2, 0.094531, 0.905469)
    assert (results["sample"]["status"], results["sample"]["requested"], results["sample"]["notes"]) == ("done", 40, 2)
    assert [(row["provider_name"], row["bodha"]["notes"]) for row in results["providers"]] == [("Elena Varga", 2)]
    assert sorted(row["agreement"]["bodha"]["em"]["direction"] for row in results["items"]) == ["lower", "match"]


async def test_a_blind_audit_freezes_bodha_from_the_claim_as_uploaded_not_the_coders_edit(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await read_note(harness, practice, icd_catalog, 1)
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes",
        headers=practice.admin,
        json={"codes": "99214-25, 20610-RT, E11.65, I12.9, N18.30, R20.2", "reason": DOCUMENTED},
    )
    assert edited.status_code == 200, edited.text
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200
    coder_id = await invite_member(harness, practice, name="Coder One", email=CODER_EMAIL, role="coder")
    body = {"scope": "practice", **PERIOD, "reviewer_ids": [coder_id]}
    started = await harness.client.post("/api/quality/samples", headers=practice.admin, json=body)
    assert started.status_code == 200, started.text

    async with SessionFactory() as db:
        [item] = (await db.scalars(select(AuditSample).where(AuditSample.run_id == started.json()["id"]))).all()
    assert reference_labels(item, "bodha") == ["99214", "E11.65", "I12.9", "N18.30", "R20.2"]
    assert reference_labels(item, "claim") == ["20610-RT", "99214-25", "E11.65", "I12.9", "N18.30", "R20.2"]


async def test_the_blind_form_shows_only_the_note_and_takes_one_valid_answer(harness, icd_catalog):
    practice, coder, sample_id, notes = await audit_setup(harness, icd_catalog)
    step = await harness.client.get(f"/api/blind-review/{sample_id}/next", headers=coder)
    item = step.json()["item"]
    assert set(item) == {"id", "position", "texts"}
    assert [text["source"] for text in item["texts"]] == ["document"]
    for code in ("99214", "99215", "E11.65", "I12.9", "R20.2", "N18.30"):
        assert code not in step.text

    path = f"/api/blind-review/items/{item['id']}"
    document = await harness.client.get(f"{path}/document", headers=coder)
    assert document.json()["url"].startswith("https://storage.test/")
    not_billable = await harness.client.post(f"{path}/answer", headers=coder, json={"em": "99214", "icd": ["E11"]})
    assert (not_billable.status_code, "E11" in not_billable.json()["message"]) == (422, True)
    not_visit = await harness.client.post(f"{path}/answer", headers=coder, json={"em": "12345", "icd": []})
    assert not_visit.status_code == 422

    answer = ANSWERS[notes[await note_of_item(item["id"])]]
    assert (await harness.client.post(f"{path}/answer", headers=coder, json=answer)).status_code == 200
    assert (await harness.client.post(f"{path}/answer", headers=coder, json=answer)).status_code == 409
    assert (await harness.client.get(f"{path}/document", headers=coder)).status_code == 409


async def test_results_stay_with_admins_and_compliance_and_items_with_their_reviewer(harness, icd_catalog):
    practice, coder, sample_id, _ = await audit_setup(harness, icd_catalog)
    assert (await harness.client.get("/api/quality/samples", headers=coder)).status_code == 403
    assert (await harness.client.get(f"/api/quality/samples/{sample_id}", headers=coder)).status_code == 403
    assert (await harness.client.get(f"/api/blind-review/{sample_id}/next", headers=practice.admin)).status_code == 404
    mine = (await harness.client.get("/api/training", headers=coder)).json()
    assert ([(row["purpose"], row["total"]) for row in mine["sets"]], mine["scores"]["claim"]["notes"]) == (
        [("audit", 2)],
        0,
    )

    item = (await harness.client.get(f"/api/blind-review/{sample_id}/next", headers=coder)).json()["item"]
    assert (
        await harness.client.get(f"/api/blind-review/items/{item['id']}/feedback", headers=coder)
    ).status_code == 409
    listed = (await harness.client.get("/api/quality/samples", headers=practice.admin)).json()["items"]
    assert [(row["status"], row["done"], row["notes"], row["reviewers"]) for row in listed] == [
        ("open", 0, 2, ["Coder One"])
    ]
    open_rows = (await harness.client.get(f"/api/quality/samples/{sample_id}", headers=practice.admin)).json()
    assert [row["bodha"] for row in open_rows["items"]] == [None, None]


async def test_a_sample_needs_approved_notes_and_reviewers_from_the_team(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await read_note(harness, practice, icd_catalog, 1)
    admin_id = await user_id("admin@lakeside.example.com")
    body = {"scope": "practice", **PERIOD, "reviewer_ids": [admin_id]}
    unapproved = await harness.client.post("/api/quality/samples", headers=practice.admin, json=body)
    assert (unapproved.status_code, unapproved.json()["message"]) == (422, "no approved notes match that period")

    stranger = {**body, "reviewer_ids": ["not-a-user"]}
    assert (await harness.client.post("/api/quality/samples", headers=practice.admin, json=stranger)).status_code == 422
    no_provider = {**body, "scope": "provider"}
    assert (
        await harness.client.post("/api/quality/samples", headers=practice.admin, json=no_provider)
    ).status_code == 422


async def test_a_specialty_sample_asks_for_150_notes(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await approved_note(harness, practice, icd_catalog, 1)
    coder_id = await invite_member(harness, practice, name="Coder One", email=CODER_EMAIL, role="coder")
    body = {"scope": "specialty", "specialty": "Internal medicine", **PERIOD, "reviewer_ids": [coder_id]}
    assert (await harness.client.post("/api/quality/samples", headers=practice.admin, json=body)).status_code == 200
    listed = (await harness.client.get("/api/quality/samples", headers=practice.admin)).json()["items"]
    assert [(row["scope"], row["specialty"], row["requested"], row["notes"]) for row in listed] == [
        ("specialty", "Internal medicine", 150, 1)
    ]


async def test_a_trainee_codes_blind_then_sees_bodha_the_claim_and_a_running_score(harness, icd_catalog):
    practice, coder, sample_id, notes = await audit_setup(harness, icd_catalog, purpose="training")
    before = (await harness.client.get("/api/training", headers=coder)).json()
    assert [(row["purpose"], row["total"], row["done"]) for row in before["sets"]] == [("training", 2, 0)]
    assert before["scores"]["claim"]["notes"] == 0

    step = await code_next(harness, coder, sample_id, notes)
    which = notes[await note_of_item(step["item"]["id"])]
    feedback = (
        await harness.client.get(f"/api/blind-review/items/{step['item']['id']}/feedback", headers=coder)
    ).json()
    assert feedback["answer"]["em"] == ANSWERS[which]["em"]
    assert feedback["bodha"]["em"] == "99214"
    assert feedback["claim"]["em"] == ("99214" if which == "first" else "99215")
    visit = next(row for row in feedback["suggestions"] if row["kind"] == "em")
    assert (visit["code_before"], visit["code_after"], visit["evidence"]) == ("99215", "99214", ["increase metformin"])

    after = (await harness.client.get("/api/training", headers=coder)).json()
    assert (after["sets"][0]["done"], after["scores"]["claim"]["notes"]) == (1, 1)
    assert after["scores"]["claim"]["em"]["successes"] == 1
    training_sets = (await harness.client.get("/api/training/sets", headers=practice.admin)).json()["items"]
    assert [(row["purpose"], row["done"]) for row in training_sets] == [("training", 1)]


BLIND_ROUTES = ("", "/document", "/defense-packet", "/claim-checks", "/day", "/addendum.txt")


async def test_a_note_in_an_open_blind_audit_stays_hidden_from_its_reviewer_until_coded(harness, icd_catalog):
    practice, coder, run_id, notes = await audit_setup(harness, icd_catalog)
    for note_id in notes:
        for route in BLIND_ROUTES:
            refused = await harness.client.get(f"/api/notes/{note_id}{route}", headers=coder)
            assert (route, refused.status_code, refused.json()["message"]) == (
                route,
                403,
                "This note is in your blind audit",
            )
        decided = await harness.client.put(
            f"/api/notes/{note_id}/decisions", headers=coder, json={"choices": {"em": "keep"}}
        )
        assert decided.status_code == 403
        assert (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).status_code == 200

    coded = await code_next(harness, coder, run_id, notes)
    coded_note = await note_of_item(coded["item"]["id"])
    still_blind = next(note_id for note_id in notes if note_id != coded_note)
    assert (await harness.client.get(f"/api/notes/{coded_note}", headers=coder)).status_code == 200
    assert (await harness.client.get(f"/api/notes/{still_blind}", headers=coder)).status_code == 403
