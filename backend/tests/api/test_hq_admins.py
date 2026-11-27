from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Activity
from tests.api.membership_helpers import SAM, access_log, membership_of, two_practices
from tests.builders import PASSWORD, practice_with_member, practice_with_provider, sign_in

REASON = "previous admin left; requested by practice owner by email"
LAKESIDE_HQ = "hq-admin@lakeside.example.com"


async def hq_of(harness, practice) -> dict[str, str]:
    return await sign_in(harness.client, LAKESIDE_HQ, secret_box=practice.secrets)


async def appoint(harness, hq, practice_id: str, **changes):
    body = {"name": "Lee Park", "email": "lee@lakeside.example.com", "reason": REASON, **changes}
    return await harness.client.post(f"/api/hq/practices/{practice_id}/admins", headers=hq, json=body)


async def hq_details(action: str) -> list[str]:
    async with SessionFactory() as db:
        return list(await db.scalars(select(Activity.detail).where(Activity.action == action)))


async def test_hq_appoints_a_new_person_as_admin_and_tells_the_existing_admins(harness):
    practice = await practice_with_provider(harness)
    hq = await hq_of(harness, practice)
    sent = len(harness.messenger.sent)
    appointed = await appoint(harness, hq, practice.id)
    assert appointed.json() == {"outcome": "invited"}
    mail = harness.messenger.sent[sent:]
    assert [to for to, _ in mail] == ["lee@lakeside.example.com", "admin@lakeside.example.com"]
    assert "/set-password#" in mail[0][1]
    assert "Bodha HQ added Lee Park as an admin of Lakeside" in mail[1][1]
    assert await hq_details("admin appointed by HQ") == [f"Lee Park: {REASON}"]
    entries = [(row["action"], row["detail"]) for row in await access_log(harness, practice.admin)]
    assert ("admin appointed by HQ", f"Lee Park: {REASON}") in entries
    token = harness.messenger.sent[sent][1].split("#")[-1]
    assert (
        await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    ).status_code == 200
    lee = await harness.client.post("/api/auth/login", json={"email": "lee@lakeside.example.com", "password": PASSWORD})
    assert lee.json()["mfa"] == "setup"


async def test_hq_adds_an_existing_account_from_another_practice_as_admin(harness):
    both = await two_practices(harness)
    harbor = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    hq = await sign_in(harness.client, "hq-admin@harbor.example.com", secret_box=harbor.secrets)
    appointed = await appoint(harness, hq, harbor.id, name="Someone Else", email=SAM)
    assert appointed.json() == {"outcome": "added"}
    to, body = harness.messenger.sent[-2]
    assert to == SAM and "added to Harbor" in body and "/set-password" not in body
    membership = await membership_of(both.sam_id, harbor.id)
    assert (membership.role, membership.status) == ("admin", "active")
    assert await hq_details("admin appointed by HQ") == [f"Sam Patel: {REASON}"]


async def test_hq_makes_an_existing_member_admin_the_same_way(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    hq = await hq_of(harness, practice)
    promoted = await appoint(harness, hq, practice.id, name="Sam Patel", email=SAM)
    assert promoted.json() == {"outcome": "promoted"}
    members = await harness.client.get("/api/team", headers=practice.admin)
    assert {member["email"]: member["role"] for member in members.json()["members"]}[SAM] == "admin"
    again = await appoint(harness, hq, practice.id, name="Sam Patel", email=SAM)
    assert (again.status_code, again.json()["message"]) == (409, "this person is already an admin of the practice")


async def test_appointing_an_admin_needs_hq_and_a_reason(harness):
    practice = await practice_with_provider(harness)
    hq = await hq_of(harness, practice)
    for reason in ("", "ok"):
        assert (await appoint(harness, hq, practice.id, reason=reason)).status_code == 422
    assert (await appoint(harness, practice.admin, practice.id)).status_code == 403
    assert (await appoint(harness, hq, "not-a-practice")).status_code == 404
