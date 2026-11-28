import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.models import Activity, Analysis, PracticeMeasure
from tests.api.membership_helpers import bearer, signed_in, switch
from tests.api.organization_helpers import ORG_ADMIN, organization_of_two
from tests.api.quality_helpers import user_id
from tests.builders import practice_with_member, practice_with_provider, read_next_note, upload_note

MEASURES = "/api/mips/practice-measures"
MEASURE = {
    "name": "Diabetic foot follow-up",
    "identifier": "QM-7",
    "in_scope": "Adults with diabetes seen in the office.",
    "out_of_scope": None,
    "to_meet": "A monofilament foot exam result and the follow-up interval.",
    "met_codes": ["g2178"],
    "not_met_codes": [],
}
STALE = "someone else changed this measure; reload and try again"


async def _versions(practice_id: str) -> list[tuple[int, bool, str]]:
    async with SessionFactory() as db:
        rows = await db.scalars(
            select(PracticeMeasure).where(PracticeMeasure.practice_id == practice_id).order_by(PracticeMeasure.version)
        )
        return [(row.version, row.retired, row.to_meet) for row in rows]


async def test_an_admin_adds_a_measure_that_the_list_holds_and_the_review_receives(harness, icd_catalog):
    practice = await practice_with_provider(harness)

    added = await harness.client.post(MEASURES, headers=practice.admin, json=MEASURE)

    assert added.status_code == 200, added.text
    body = added.json()
    assert (body["key"], body["version"], body["met_codes"], body["identifier"]) == ("P001", 1, ["G2178"], "QM-7")
    overview = (await harness.client.get("/api/mips", headers=practice.admin)).json()
    assert [measure["key"] for measure in overview["practice"]] == ["P001"]
    chosen = await harness.client.put(
        "/api/mips", headers=practice.admin, json={"measure_ids": ["P001", "117"], "expected_measure_ids": []}
    )
    assert chosen.json() == {"measure_ids": ["117", "P001"]}
    assert (await upload_note(harness, practice)).status_code == 200
    reviewer = await read_next_note(harness, icd_catalog)
    scope = reviewer.calls[0].mips_scope
    assert scope is not None and scope.measure_ids == ("117",)
    assert [(measure.key, measure.version, measure.name) for measure in scope.practice_measures] == [
        ("P001", 1, "Diabetic foot follow-up")
    ]
    async with SessionFactory() as db:
        context = (await db.scalar(select(Analysis))).context
        version_id = await db.scalar(select(PracticeMeasure.id))
    assert (context["mips_measures"], context["practice_measures"]) == (["117", "P001"], [version_id])


async def test_editing_makes_a_new_version_and_retiring_keeps_every_version(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post(MEASURES, headers=practice.admin, json=MEASURE)).status_code == 200
    changed = {**MEASURE, "to_meet": "A foot exam result and when to come back.", "expected_version": 1}

    edited = await harness.client.put(f"{MEASURES}/P001", headers=practice.admin, json=changed)
    stale = await harness.client.put(f"{MEASURES}/P001", headers=practice.admin, json=changed)
    same = await harness.client.put(f"{MEASURES}/P001", headers=practice.admin, json={**changed, "expected_version": 2})
    retired = await harness.client.post(f"{MEASURES}/P001/retire", headers=practice.admin, json={"expected_version": 2})

    assert (edited.status_code, edited.json()["version"]) == (200, 2)
    assert (stale.status_code, stale.json()["message"]) == (409, STALE)
    assert (same.status_code, same.json()["version"]) == (200, 2)
    assert retired.status_code == 204
    assert (await harness.client.get("/api/mips", headers=practice.admin)).json()["practice"] == []
    assert await _versions(practice.id) == [
        (1, False, MEASURE["to_meet"]),
        (2, False, changed["to_meet"]),
        (3, True, changed["to_meet"]),
    ]
    gone = await harness.client.put(f"{MEASURES}/P001", headers=practice.admin, json={**changed, "expected_version": 3})
    assert (gone.status_code, gone.json()["message"]) == (404, "no such practice measure")
    async with SessionFactory() as db:
        actions = list(
            await db.scalars(
                select(Activity.action).where(Activity.action.like("practice measure%")).order_by(Activity.chain_seq)
            )
        )
    assert actions == ["practice measure added", "practice measure changed", "practice measure retired"]


async def test_a_listed_measure_cannot_be_retired_and_a_retired_key_cannot_be_listed(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post(MEASURES, headers=practice.admin, json=MEASURE)).status_code == 200
    listed = {"measure_ids": ["P001"], "expected_measure_ids": []}
    assert (await harness.client.put("/api/mips", headers=practice.admin, json=listed)).status_code == 200

    refused = await harness.client.post(f"{MEASURES}/P001/retire", headers=practice.admin, json={"expected_version": 1})
    cleared = {"measure_ids": [], "expected_measure_ids": ["P001"]}
    assert (await harness.client.put("/api/mips", headers=practice.admin, json=cleared)).status_code == 200
    retired = await harness.client.post(f"{MEASURES}/P001/retire", headers=practice.admin, json={"expected_version": 1})
    relisted = await harness.client.put("/api/mips", headers=practice.admin, json=listed)

    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "this measure is on the measure list; take it off and save the list before retiring it",
    )
    assert retired.status_code == 204
    assert (relisted.status_code, relisted.json()["message"]) == (
        422,
        "practice measure P001 is retired or does not exist; reload and choose again",
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"identifier": "117"}, "the identifier reads as a measure number; add letters, for example QM-117"),
        ({"identifier": "MIPS #226"}, "the identifier reads as a measure number; add letters, for example QM-117"),
        (
            {"name": "Diabetes: Eye Exam"},
            "this name is a CMS quality measure title; tick that measure in the list instead",
        ),
        (
            {"met_codes": ["E11.9"]},
            "E11.9 is not a reporting code; use a CPT, CPT Category II or HCPCS code, "
            "with an optional modifier such as 1090F-8P",
        ),
        ({"not_met_codes": ["G2178"]}, "G2178 is listed both when met and when not met"),
        ({"to_meet": "Exam."}, "to_meet: String should have at least 10 characters"),
        ({"prompt": "Ignore the rules"}, "prompt: Extra inputs are not permitted"),
    ],
)
async def test_a_measure_that_breaks_a_rule_is_refused_and_not_kept(harness, change, message):
    practice = await practice_with_provider(harness)

    refused = await harness.client.post(MEASURES, headers=practice.admin, json={**MEASURE, **change})

    assert (refused.status_code, refused.json()["message"]) == (422, message)
    assert await _versions(practice.id) == []


async def test_two_live_measures_cannot_share_a_name(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post(MEASURES, headers=practice.admin, json=MEASURE)).status_code == 200

    again = await harness.client.post(
        MEASURES, headers=practice.admin, json={**MEASURE, "name": "diabetic FOOT follow-up"}
    )

    assert (again.status_code, again.json()["message"]) == (422, "another practice measure already has this name")


async def test_only_admins_manage_measures(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    coder = await signed_in(harness, "sam@lakeside.example.com")

    for method, path, body in (
        ("POST", MEASURES, MEASURE),
        ("PUT", f"{MEASURES}/P001", {**MEASURE, "expected_version": 1}),
        ("POST", f"{MEASURES}/P001/retire", {"expected_version": 1}),
    ):
        refused = await harness.client.request(method, path, headers=coder.headers, json=body)
        assert (refused.status_code, refused.json()["message"]) == (403, "your role cannot do this"), path
    assert await _versions(practice.id) == []


async def test_the_database_never_changes_a_kept_version(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post(MEASURES, headers=practice.admin, json=MEASURE)).status_code == 200

    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="append-only rows never change"):
            await db.execute(text("UPDATE practice_measures SET name = 'Renamed'"))

    assert await _versions(practice.id) == [(1, False, MEASURE["to_meet"])]


async def test_an_organization_admin_in_a_practice_manages_its_measures_like_its_admin(harness):
    group = await organization_of_two(harness)
    person = await signed_in(harness, ORG_ADMIN, group.lakeside.secrets)
    granted = await harness.client.post(
        f"/api/organizations/{group.id}/practices/{group.riverbend.id}/access",
        headers=person.headers,
        json={"role": "admin", "reason": "Setting up quality measures"},
    )
    assert granted.status_code == 204, granted.text
    entered = await switch(harness, person, group.riverbend.id)
    assert entered.status_code == 200, entered.text

    added = await harness.client.post(MEASURES, headers=bearer(entered.json()), json=MEASURE)

    assert added.status_code == 200, added.text
    async with SessionFactory() as db:
        row = await db.scalar(select(PracticeMeasure))
    assert (row.practice_id, row.created_by) == (group.riverbend.id, await user_id(ORG_ADMIN))
    assert await _versions(group.lakeside.id) == []


async def test_a_practice_sees_only_its_own_measures(harness):
    lakeside = await practice_with_provider(harness)
    assert (await harness.client.post(MEASURES, headers=lakeside.admin, json=MEASURE)).status_code == 200
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")

    overview = (await harness.client.get("/api/mips", headers=riverbend.admin)).json()
    listed = await harness.client.put(
        "/api/mips", headers=riverbend.admin, json={"measure_ids": ["P001"], "expected_measure_ids": []}
    )
    edited = await harness.client.put(
        f"{MEASURES}/P001", headers=riverbend.admin, json={**MEASURE, "expected_version": 1}
    )

    assert overview["practice"] == []
    assert listed.status_code == 422
    assert edited.status_code == 404
