from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Activity, User
from app.scripts.invite_hq import invite_people, main
from tests.builders import ADMIN_SITE, create_hq_user, practice_with_provider
from tests.fakes import FakeMessenger

ASHA = "Asha Rao <asha@bodha.example.com>"
RAVI = "Ravi Menon <Ravi@Bodha.example.com>"
NOT_A_PERSON = 'not in the form "Full Name <email>"; skipped'


async def hq_rows() -> dict[str, tuple[str, str, str]]:
    async with SessionFactory() as db:
        rows = await db.execute(select(User.email, User.id, User.name, User.status).where(User.role == "hq"))
        return {email: (user_id, name, status) for email, user_id, name, status in rows.all()}


async def activity_actions() -> list[tuple[str, str, str | None]]:
    async with SessionFactory() as db:
        rows = await db.execute(
            select(Activity.action, Activity.actor_name, Activity.detail).order_by(Activity.created_at)
        )
        return [tuple(row) for row in rows.all()]


async def test_new_people_become_invited_hq_accounts_with_a_link_to_the_admin_host(two_hosts):
    messenger = FakeMessenger()
    lines = await invite_people([ASHA, RAVI], messenger)
    rows = await hq_rows()
    assert {email: (name, status) for email, (_, name, status) in rows.items()} == {
        "asha@bodha.example.com": ("Asha Rao", "invited"),
        "ravi@bodha.example.com": ("Ravi Menon", "invited"),
    }
    assert lines == [
        f"1. Asha Rao: invited (user {rows['asha@bodha.example.com'][0]})",
        f"2. Ravi Menon: invited (user {rows['ravi@bodha.example.com'][0]})",
    ]
    assert [to for to, _ in messenger.sent] == ["asha@bodha.example.com", "ravi@bodha.example.com"]
    assert all(f"{ADMIN_SITE}/set-password#" in body for _, body in messenger.sent)
    links = [body.split("#")[1] for _, body in messenger.sent]
    assert not any(link in line for link in links for line in lines)
    assert await activity_actions() == [
        ("hq member invited", "Bodha", "Asha Rao"),
        ("hq member invited", "Bodha", "Ravi Menon"),
    ]


async def test_running_again_resends_pending_invites_renames_and_leaves_active_accounts_alone(two_hosts):
    await create_hq_user("owner@bodha.example.com")
    messenger = FakeMessenger()
    await invite_people([ASHA], messenger)
    again = await invite_people([ASHA, "Kiran Shah <owner@bodha.example.com>"], messenger)
    rows = await hq_rows()
    assert again == [
        f"1. Asha Rao: invite sent again (user {rows['asha@bodha.example.com'][0]})",
        f"2. Kiran Shah: already active, renamed from Bodha Admin (user {rows['owner@bodha.example.com'][0]})",
    ]
    assert rows["owner@bodha.example.com"][1:] == ("Kiran Shah", "active")
    assert [to for to, _ in messenger.sent] == ["asha@bodha.example.com", "asha@bodha.example.com"]
    assert ("hq member renamed", "Bodha", "Bodha Admin to Kiran Shah") in await activity_actions()
    assert ("hq invite resent", "Bodha", "Asha Rao") in await activity_actions()


async def test_an_argument_without_a_name_and_an_email_is_skipped_and_the_rest_still_run(two_hosts):
    messenger = FakeMessenger()
    lines = await invite_people(["asha@bodha.example.com", "Asha Rao <not-an-email>", RAVI], messenger)
    assert lines[:2] == [f"1. {NOT_A_PERSON}", f"2. {NOT_A_PERSON}"]
    assert lines[2].startswith("3. Ravi Menon: invited (user ")
    assert list(await hq_rows()) == ["ravi@bodha.example.com"]


async def test_on_one_host_an_email_a_practice_uses_is_refused_for_that_person_only(harness):
    await practice_with_provider(harness)
    lines = await invite_people(["Lake Admin <admin@lakeside.example.com>", ASHA], FakeMessenger())
    assert lines[0] == "1. Lake Admin: someone already uses that email; skipped"
    assert lines[1].startswith("2. Asha Rao: invited (user ")


def test_without_arguments_it_prints_its_usage_and_fails(capsys):
    assert main([]) == 2
    assert capsys.readouterr().err.startswith('usage: python -m app.scripts.invite_hq "Full Name <email>"')
