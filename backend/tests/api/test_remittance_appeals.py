from __future__ import annotations

from datetime import date

from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import RemittanceLine
from app.services.remittance_outcomes import DEFAULT_APPEAL_DAYS, line_appeal_by
from tests.api.remittance_helpers import era, post_era, three_notes
from tests.builders import practice_with_provider

PAID_ON = date(2026, 11, 24)


async def _uploaded(harness):
    practice = await practice_with_provider(harness)
    reyes, _, lindqvist = await three_notes(harness, practice)
    remittance_id = (await post_era(harness, practice.admin, era(reyes, lindqvist))).json()["ids"][0]
    return practice, remittance_id


async def _lines(harness, practice, remittance_id) -> list[dict]:
    response = await harness.client.get(f"/api/remittances/{remittance_id}", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()["lines"]


async def _save_windows(harness, practice, days: dict[str, int]) -> dict[str, int]:
    saved = await harness.client.put("/api/remittances/appeal-days", headers=practice.admin, json={"days": days})
    assert saved.status_code == 200, saved.text
    return saved.json()


async def _next_appeal_by(harness, practice) -> str | None:
    listing = (await harness.client.get("/api/remittances", headers=practice.admin)).json()
    return listing["items"][0]["next_appeal_by"]


async def test_appeal_dates_move_when_the_appeal_windows_change(harness):
    practice, remittance_id = await _uploaded(harness)
    before = await _lines(harness, practice, remittance_id)
    assert [(line["status"], line["appeal_by"]) for line in before] == [
        ("downcoded", "2027-03-24"),
        ("paid_as_billed", None),
        ("denied", "2027-05-23"),
        ("unmatched", "2027-05-23"),
    ]

    saved = await _save_windows(harness, practice, {"medicare": 90, "medicare_advantage": 65, "commercial": 30})
    assert saved == {"commercial": 30, "medicare": 90, "medicare_advantage": 65, "medicaid": 180, "other": 180}

    after = await _lines(harness, practice, remittance_id)
    assert [(line["status"], line["appeal_by"]) for line in after] == [
        ("downcoded", "2027-02-22"),
        ("paid_as_billed", None),
        ("denied", "2026-12-24"),
        ("unmatched", "2026-12-24"),
    ]
    assert await _next_appeal_by(harness, practice) == "2026-12-24"
    draft = await harness.client.get(f"/api/remittances/lines/{after[0]['id']}/appeal", headers=practice.admin)
    assert draft.json()["appeal_by"] == "2027-02-22"


async def test_a_line_keeps_the_plan_type_and_no_stored_date(harness):
    await _uploaded(harness)
    async with SessionFactory() as db:
        columns = (RemittanceLine.status, RemittanceLine.appeal_plan_type, RemittanceLine.appeal_by)
        stored = {status: (plan_type, appeal_by) for status, plan_type, appeal_by in await db.execute(select(*columns))}
    assert stored == {
        "downcoded": ("medicare", None),
        "paid_as_billed": (None, None),
        "denied": ("commercial", None),
        "unmatched": ("commercial", None),
    }


async def test_a_line_stored_before_plan_types_keeps_its_stored_date(harness):
    practice, remittance_id = await _uploaded(harness)
    async with SessionFactory() as db:
        await db.execute(
            update(RemittanceLine)
            .where(RemittanceLine.status == "denied")
            .values(appeal_plan_type=None, appeal_by=date(2026, 12, 1))
        )
        await db.commit()
    await _save_windows(harness, practice, {"commercial": 30})

    lines = await _lines(harness, practice, remittance_id)
    assert [(line["status"], line["appeal_by"]) for line in lines] == [
        ("downcoded", "2027-03-24"),
        ("paid_as_billed", None),
        ("denied", "2026-12-01"),
        ("unmatched", "2026-12-24"),
    ]
    assert await _next_appeal_by(harness, practice) == "2026-12-01"


def test_the_appeal_date_is_the_payment_date_plus_the_current_window():
    windows = {**DEFAULT_APPEAL_DAYS, "medicaid": 365}
    assert line_appeal_by(PAID_ON, "medicaid", None, windows) == date(2027, 11, 24)
    assert line_appeal_by(PAID_ON, "medicare", date(2026, 1, 1), windows) == date(2027, 3, 24)
    assert line_appeal_by(PAID_ON, None, date(2027, 1, 15), windows) == date(2027, 1, 15)
    assert line_appeal_by(PAID_ON, None, None, windows) is None
