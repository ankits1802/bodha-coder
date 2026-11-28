from __future__ import annotations

import json
from typing import Any

from tests.builders import Harness, Practice
from tests.fakes import text_pdf

VARGA = {
    "name": "Elena Varga",
    "credential": "MD",
    "specialty": "Internal medicine",
    "npi": "1234567893",
    "place_code": "11",
    "email": "varga@clinic.example.com",
}


async def add_payer(harness: Harness, practice: Practice, name: str, plan_type: str, *, active: bool = True) -> str:
    added = await harness.client.post(
        "/api/practice/payers", headers=practice.admin, json={"name": name, "plan_type": plan_type, "active": active}
    )
    assert added.status_code == 200, added.text
    return added.json()["id"]


async def set_usual_payer(harness: Harness, practice: Practice, payer: str | None):
    return await harness.client.put(
        f"/api/providers/{practice.provider_id}", headers=practice.admin, json={**VARGA, "payer": payer}
    )


async def upload_with_payers(
    harness: Harness, practice: Practice, details: list[dict[str, Any]], *, batch_payer: str | None = None
):
    form = {
        "provider_id": practice.provider_id,
        "service_date": "2026-11-25",
        "place_code": "11",
        "visit_type": "Established patient",
        "details": json.dumps(details),
    }
    if batch_payer is not None:
        form["payer"] = batch_payer
    files = [("files", (f"visit-{n}.pdf", text_pdf(f"Visit {n}"), "application/pdf")) for n in range(len(details))]
    return await harness.client.post("/api/uploads", headers=practice.admin, data=form, files=files)


async def payers_by_file(harness: Harness, practice: Practice) -> dict[str, str | None]:
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    assert listing.status_code == 200, listing.text
    return {row["file_name"]: row["payer"] for row in listing.json()["items"]}
