from __future__ import annotations

from typing import Any

from tests.e2e_seed.accounts import Account, practice_caller
from tests.e2e_seed.api import Caller, practice_host
from tests.e2e_seed.notes import SERVICE_DAY, SyntheticNote, upload_notes
from tests.e2e_seed.organizations import create_organization
from tests.e2e_seed.practices import VARGA_NPI, Practice, Provider, add_payer, end_plan, send_invite
from tests.e2e_seed.review import adopt_signature, approve, ask_provider, assign_training, draw_audit, verification_code
from tests.e2e_seed.run import SeedRun

__all__ = ["sweep_day"]

MEMBERS = {
    "coder": "Casey Coder",
    "cdi": "Robin Clarke",
    "compliance": "Morgan Officer",
    "biller": "Blake Biller",
    "viewer": "Vic Viewer",
}
TWO_STEP_ROLES = {"compliance"}
NOTES = {
    "approved": ("Hugo", "Tanaka", "matches"),
    "signed": ("Freya", "Olsen", "matches"),
    "ready": ("Iris", "Moreau", "matches"),
    "coder": ("Ines", "Marlowe", "billed_too_high"),
    "provider": ("Nadia", "Brennan", "cdi_query"),
    "asked": ("Owen", "Halvorsen", "cdi_query"),
    "compliance": ("Lena", "Castellano", "audit_risk"),
}
INVITEE = "Pat Pending"
DEMO = {"name": "Jamie Prospect", "organization": "Synthetic Valley Clinic", "message": "Synthetic demo request"}


def person(account: Account, practice_id: str | None) -> dict[str, Any]:
    return {
        "id": account.id,
        "name": account.name,
        "email": account.email,
        "role": account.role,
        "practice_id": practice_id,
    }


async def team(run: SeedRun, practice: Practice) -> dict[str, Account]:
    people = {"admin": practice.admin}
    for role, name in MEMBERS.items():
        people[role] = await run.member(practice, name=name, role=role, two_step=role in TWO_STEP_ROLES)
    return people


async def read_notes(run: SeedRun, admin: Caller, provider: Provider) -> dict[str, dict[str, str]]:
    notes = {key: SyntheticNote(first, last, outcome, provider) for key, (first, last, outcome) in NOTES.items()}
    ids = await upload_notes(run.api, admin, list(notes.values()))
    return {key: {"id": ids[note.patient], "patient": note.patient} for key, note in notes.items()}


async def review_work(run: SeedRun, admin: Caller, people: dict[str, Account], notes: dict[str, Any]) -> dict[str, Any]:
    await adopt_signature(run.api, admin, name=people["admin"].name)
    for key in ("approved", "signed"):
        await approve(run.api, admin, notes[key]["id"])
    coder = people["coder"].id
    samples = {
        "audit": await draw_audit(run.api, admin, day=SERVICE_DAY, reviewer_id=coder),
        "training": await assign_training(run.api, admin, day=SERVICE_DAY, trainee_id=coder),
    }
    await ask_provider(run.api, admin, notes["asked"]["id"])
    return {"samples": samples, "verification_code": await verification_code(run.api, admin, notes["approved"]["id"])}


async def connect_settings(run: SeedRun, admin: Caller, organization_id: str) -> None:
    await run.api.send(admin, "POST", "/api/practice/sso")
    await run.api.send(admin, "POST", f"/api/organizations/{organization_id}/sso")
    await run.api.send(admin, "POST", "/api/practice/email-intake/address")


async def busy_practice(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Sweep Clinic")
    people = await team(run, practice)
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    await add_payer(run.api, practice, name="Synthetic Health Plan", payer_id="SYN01", plan_type="medicare")
    admin = await practice_caller(practice.admin, practice.id)
    notes = await read_notes(run, admin, provider)
    work = await review_work(run, admin, people, notes)
    organization = await create_organization(
        run.api, await run.hq(), name=run.named("Sweep Health"), practices=[practice], admin=practice.admin
    )
    await connect_settings(run, admin, organization.id)
    return {
        "practice": {"id": practice.id, "name": practice.name},
        "organization": {"id": organization.id, "name": organization.name},
        "people": {key: person(account, practice.id) for key, account in people.items()},
        "provider": provider.view(),
        "notes": notes,
        **work,
    }


async def sweep_day(run: SeedRun) -> dict[str, Any]:
    busy = await busy_practice(run)
    empty = await run.practice("Empty Clinic", admin_mailbox="empty-admin")
    invitee = run.email("invitee")
    await send_invite(run.api, empty, name=INVITEE, email=invitee, role="coder")
    lapsed = await run.practice("Lapsed Clinic", admin_mailbox="lapsed-admin")
    await end_plan(lapsed)
    hq = await run.hq_person("Harper HQ")
    demo = {**DEMO, "email": run.email("prospect")}
    await run.api.send(Caller(None, practice_host()), "POST", "/api/demo-requests", json=demo)
    busy["people"] |= {
        "empty_admin": person(empty.admin, empty.id),
        "lapsed_admin": person(lapsed.admin, lapsed.id),
        "hq": person(hq, None),
    }
    return {
        **busy,
        "empty": {"id": empty.id, "name": empty.name},
        "lapsed": {"id": lapsed.id, "name": lapsed.name},
        "invitee": invitee,
    }
