from __future__ import annotations

import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from tests.e2e_seed.accounts import practice_caller
from tests.e2e_seed.notes import SyntheticNote, upload_notes, write_pdfs
from tests.e2e_seed.organizations import create_organization
from tests.e2e_seed.practices import VARGA_NPI
from tests.e2e_seed.review import adopt_signature, approve, assign, verification_code
from tests.e2e_seed.run import SeedRun
from tests.e2e_seed.sweep import sweep_day

__all__ = ["SCENARIOS"]

Scenario = Callable[[SeedRun], Awaitable[dict[str, Any]]]


async def admin_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Admin Clinic")
    return {"admin": practice.admin.view(), "practice": practice.name}


async def upload_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Upload Clinic")
    coder = await run.member(practice, name="Casey Coder", role="coder")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    notes = [
        SyntheticNote("Mara", "Lindqvist", "billed_too_high", provider),
        SyntheticNote("Owen", "Halvorsen", "matches", provider),
    ]
    folder = Path(tempfile.mkdtemp(prefix=f"bodha-e2e-{run.marker}-"))
    return {
        "coder": coder.view(),
        "provider": provider.view(),
        "files": write_pdfs(folder, notes),
        "patients": [note.patient for note in notes],
    }


async def coder_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Coder Clinic")
    coder = await run.member(practice, name="Casey Coder", role="coder")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    notes = [
        SyntheticNote("Ines", "Marlowe", "billed_too_high", provider),
        SyntheticNote("Tomas", "Ekberg", "billed_too_high", provider),
    ]
    ids = await upload_notes(run.api, await practice_caller(coder, practice.id), notes)
    return {"coder": coder.view(), "notes": [{"patient": patient, "id": ids[patient]} for patient in ids]}


async def provider_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Query Clinic")
    coder = await run.member(practice, name="Casey Coder", role="coder")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    note = SyntheticNote("Nadia", "Brennan", "cdi_query", provider)
    ids = await upload_notes(run.api, await practice_caller(coder, practice.id), [note])
    return {
        "practice": practice.name,
        "coder": coder.view(),
        "provider": provider.view(),
        "note": {"patient": note.patient, "id": ids[note.patient]},
    }


async def compliance_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Compliance Clinic")
    officer = await run.member(practice, name="Morgan Officer", role="compliance", two_step=True)
    coder = await run.member(practice, name="Casey Coder", role="coder")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    note = SyntheticNote("Lena", "Castellano", "audit_risk", provider)
    admin = await practice_caller(practice.admin, practice.id)
    ids = await upload_notes(run.api, admin, [note])
    await assign(run.api, admin, [ids[note.patient]], coder.id)
    return {
        "officer": officer.view(),
        "coder": coder.view(),
        "note": {"patient": note.patient, "id": ids[note.patient]},
    }


async def biller_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Billing Clinic")
    biller = await run.member(practice, name="Blake Biller", role="biller")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    notes = [
        SyntheticNote("Hugo", "Tanaka", "matches", provider),
        SyntheticNote("Freya", "Olsen", "matches", provider),
    ]
    admin = await practice_caller(practice.admin, practice.id)
    ids = await upload_notes(run.api, admin, notes)
    await adopt_signature(run.api, admin, name=practice.admin.name)
    for note_id in ids.values():
        await approve(run.api, admin, note_id)
    return {"biller": biller.view(), "patients": list(ids)}


async def organization_day(run: SeedRun) -> dict[str, Any]:
    north = await run.practice("North Clinic")
    south = await run.second_practice("South Clinic", north.admin)
    organization = await create_organization(
        run.api, await run.hq(), name=run.named("Lakes Health"), practices=[north, south], admin=north.admin
    )
    return {
        "admin": north.admin.view(),
        "practices": [north.name, south.name],
        "organization": {"id": organization.id, "name": organization.name},
        "domain": f"synthetic-{run.marker}.example.com",
    }


async def hq_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Renewal Clinic")
    person = await run.hq_person("Harper HQ")
    return {"hq": person.view(), "practice": {"id": practice.id, "name": practice.name}}


async def verify_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Signed Clinic")
    provider = await run.provider(practice, name="Elena Varga", npi=VARGA_NPI)
    note = SyntheticNote("Iris", "Moreau", "matches", provider)
    admin = await practice_caller(practice.admin, practice.id)
    ids = await upload_notes(run.api, admin, [note])
    await adopt_signature(run.api, admin, name=practice.admin.name)
    await approve(run.api, admin, ids[note.patient])
    code = await verification_code(run.api, admin, ids[note.patient])
    return {"code": code, "practice": practice.name, "signer": practice.admin.name}


async def canary_day(run: SeedRun) -> dict[str, Any]:
    practice = await run.practice("Canary Clinic")
    person = await run.hq_person("Casey Canary")
    return {"practice": practice.admin.view(), "hq": person.view()}


SCENARIOS: dict[str, Scenario] = {
    "admin-day": admin_day,
    "upload-day": upload_day,
    "coder-day": coder_day,
    "provider-day": provider_day,
    "compliance-day": compliance_day,
    "biller-day": biller_day,
    "organization-day": organization_day,
    "hq-day": hq_day,
    "verify-day": verify_day,
    "canary-day": canary_day,
    "sweep-day": sweep_day,
}
