from __future__ import annotations

import re
from datetime import date

from app.adapters.pdf_text import read_pdf_text
from app.core.db import SessionFactory
from app.models import Note
from app.services.placement import current_decisions, current_findings
from app.services.routing import choices_for, open_questions
from tests.e2e_seed.api import Api, Caller, SeedFailed
from tests.fakes import signature_data_url

__all__ = ["adopt_signature", "approve", "ask_provider", "assign", "assign_training", "draw_audit", "verification_code"]

VERIFY_LINK = re.compile(r"verify\?code=(?P<code>[A-Z0-9]{4}-?[A-Z0-9]{4}-?[A-Z0-9]{4})")


async def adopt_signature(api: Api, caller: Caller, *, name: str) -> str:
    body = {"source": "typed", "typed_name": name, "image": signature_data_url()}
    drafted = await api.send(caller, "POST", "/api/signature/drafts", json=body)
    await api.send(caller, "POST", f"/api/signature/drafts/{drafted['id']}/adopt")
    return drafted["id"]


async def approve(api: Api, caller: Caller, note_id: str) -> None:
    await api.send(caller, "POST", f"/api/notes/{note_id}/approve")


async def assign(api: Api, caller: Caller, note_ids: list[str], user_id: str) -> None:
    await api.send(caller, "POST", "/api/notes/assign", json={"note_ids": note_ids, "user_id": user_id})


async def verification_code(api: Api, caller: Caller, note_id: str) -> str:
    packet = await api.download(caller, f"/api/notes/{note_id}/defense-packet")
    found = VERIFY_LINK.search(read_pdf_text(packet).text.replace("\n", ""))
    if found is None:
        raise SeedFailed(f"the defense packet of note {note_id} carries no verification code")
    return found["code"]


async def ask_provider(api: Api, caller: Caller, note_id: str) -> str:
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        findings = await current_findings(db, note)
        keys = [
            item.key for item in open_questions(findings, choices_for(findings, await current_decisions(db, note_id)))
        ]
    if not keys:
        raise SeedFailed(f"note {note_id} has no open question to ask its provider")
    body = {"questions": [{"key": key, "text": ""} for key in keys], "channel": "email", "hold": True}
    asked = await api.send(caller, "POST", f"/api/notes/{note_id}/ask", json=body)
    return asked["request_id"]


async def draw_audit(api: Api, caller: Caller, *, day: date, reviewer_id: str) -> str:
    body = {
        "scope": "practice",
        "start": day.isoformat(),
        "end": day.isoformat(),
        "reviewer_ids": [reviewer_id],
        "size": 1,
    }
    return (await api.send(caller, "POST", "/api/quality/samples", json=body))["id"]


async def assign_training(api: Api, caller: Caller, *, day: date, trainee_id: str) -> str:
    body = {"trainee_id": trainee_id, "start": day.isoformat(), "end": day.isoformat(), "size": 1}
    return (await api.send(caller, "POST", "/api/training/sets", json=body))["id"]
