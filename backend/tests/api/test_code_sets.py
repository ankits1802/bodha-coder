from __future__ import annotations

from app.core.db import SessionFactory
from app.models import CodeSet
from app.services.code_sets import latest_codes_for
from tests.builders import reviewed_note


async def test_the_latest_code_set_of_each_note_is_read_for_many_notes_at_once(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    async with SessionFactory() as db:
        db.add(
            CodeSet(
                note_id=note_id,
                kind="billed",
                revision=2,
                codes=[{"code": "99213", "type": "CPT", "modifiers": ["25"], "units": 1}],
                reason="edited",
            )
        )
        await db.commit()
        billed = await latest_codes_for(db, "billed", [note_id, "no-such-note"])
        final = await latest_codes_for(db, "final", [note_id])
        nothing = await latest_codes_for(db, "billed", [])

    assert list(billed) == [note_id]
    assert [(code.code, code.type, code.modifiers) for code in billed[note_id]] == [("99213", "CPT", ("25",))]
    assert (final, nothing) == ({}, {})
