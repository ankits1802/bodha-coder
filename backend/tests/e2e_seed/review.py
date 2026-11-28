from __future__ import annotations

import re

from app.adapters.pdf_text import read_pdf_text
from tests.e2e_seed.api import Api, Caller, SeedFailed
from tests.fakes import signature_data_url

__all__ = ["adopt_signature", "approve", "assign", "verification_code"]

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
