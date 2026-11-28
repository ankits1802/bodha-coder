from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import Practice, UsageEvent, utcnow
from tests.api.membership_helpers import signed_in
from tests.api.quality_helpers import user_id
from tests.builders import maintenance, practice_with_member, practice_with_provider, sign_in

EVENTS = "/api/usage/events"
ADMIN = "admin@lakeside.example.com"
CODER = "sam@lakeside.example.com"
HQ_EMAIL = "hq-admin@lakeside.example.com"
STORED_COLUMNS = {
    "id",
    "created_at",
    "practice_id",
    "user_id",
    "role",
    "client_event_id",
    "kind",
    "task",
    "step",
    "outcome",
    "duration_ms",
    "first_decision_ms",
    "key_inputs",
    "pointer_inputs",
    "key_decisions",
    "pointer_decisions",
}


def task(**change: Any) -> dict[str, Any]:
    event = {
        "kind": "task",
        "event_id": str(uuid4()),
        "task": "note_review",
        "outcome": "completed",
        "duration_ms": 95_000,
        "first_decision_ms": 20_000,
        "key_inputs": 12,
        "pointer_inputs": 4,
        "key_decisions": 3,
        "pointer_decisions": 1,
    }
    return {**event, **change}


def stall(**change: Any) -> dict[str, Any]:
    return {
        "kind": "stall",
        "event_id": str(uuid4()),
        "task": "note_review",
        "step": "findings",
        "duration_ms": 75_000,
        **change,
    }


async def _rows() -> list[UsageEvent]:
    async with SessionFactory() as db:
        return list(await db.scalars(select(UsageEvent).order_by(UsageEvent.kind)))


def test_a_usage_row_holds_only_ids_timings_counts_and_step_names():
    assert set(UsageEvent.__table__.columns.keys()) == STORED_COLUMNS


async def test_a_coder_sends_timings_that_are_kept_once_with_the_session_role(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    coder = await signed_in(harness, CODER)
    batch = {"events": [task(), stall()]}

    first = await harness.client.post(EVENTS, headers=coder.headers, json=batch)
    again = await harness.client.post(EVENTS, headers=coder.headers, json=batch)

    assert (first.status_code, again.status_code) == (204, 204)
    stalled, timed = await _rows()
    assert (stalled.kind, stalled.step, stalled.duration_ms, stalled.outcome) == ("stall", "findings", 75_000, None)
    assert (timed.kind, timed.task, timed.outcome, timed.duration_ms, timed.first_decision_ms) == (
        "task",
        "note_review",
        "completed",
        95_000,
        20_000,
    )
    assert (timed.key_inputs, timed.pointer_inputs, timed.key_decisions, timed.pointer_decisions) == (12, 4, 3, 1)
    assert {(row.role, row.practice_id, row.user_id) for row in (stalled, timed)} == {
        ("coder", practice.id, await user_id(CODER))
    }


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ([stall(step="queue")], "the queue step is not part of the note_review task"),
        ([stall(duration_ms=30_000)], "a stall lasts at least 60 seconds"),
        ([task(task="upload")], "the upload task has no findings to decide"),
        ([task(first_decision_ms=None)], "time to first decision comes with at least one decision, and only then"),
        ([task(key_decisions=0, pointer_decisions=0)], "time to first decision comes with at least one decision"),
        ([task(first_decision_ms=200_000)], "the first decision cannot come after the task ended"),
        ([task(duration_ms=-1)], "greater than or equal to 0"),
        ([task(duration_ms=5 * 60 * 60 * 1000)], "less than or equal to 14400000"),
        ([task(task="search")], "events.1"),
        ([task(note_id="5f1c")], "Extra inputs are not permitted"),
        ([task(page="/notes/5f1c?patient=Reyes")], "Extra inputs are not permitted"),
        ([stall(text="patient was confused")], "Extra inputs are not permitted"),
        ([task(step="findings")], "Extra inputs are not permitted"),
        ([task() for _ in range(51)], "events: List should have at most 50 items"),
    ],
)
async def test_a_timing_that_breaks_a_rule_is_refused_and_nothing_is_kept(harness, events, message):
    practice = await practice_with_provider(harness)

    refused = await harness.client.post(EVENTS, headers=practice.admin, json={"events": [task(), *events]})

    assert refused.status_code == 422, refused.text
    assert message in refused.json()["message"]
    assert await _rows() == []


async def test_an_empty_batch_is_refused(harness):
    practice = await practice_with_provider(harness)

    refused = await harness.client.post(EVENTS, headers=practice.admin, json={"events": []})

    assert (refused.status_code, refused.json()["message"]) == (
        422,
        "events: List should have at least 1 item after validation, not 0",
    )


async def test_hq_records_nothing_practice_side(harness):
    practice = await practice_with_provider(harness)
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=practice.secrets)

    refused = await harness.client.post(EVENTS, headers=hq, json={"events": [task()]})

    assert (refused.status_code, refused.json()["message"]) == (403, "your role cannot do this")
    assert await _rows() == []


async def test_a_billing_only_session_records_nothing(harness):
    practice = await practice_with_provider(harness)
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice.id).values(renews_on=date(2025, 12, 31)))
        await db.commit()

    refused = await harness.client.post(EVENTS, headers=practice.admin, json={"events": [task()]})

    assert (refused.status_code, refused.json()["error"]) == (403, "plan_ended")
    assert await _rows() == []


async def _seed(practice_id: str, email: str, role: str, *events: dict[str, Any], days_ago: int = 0) -> None:
    person = await user_id(email)
    async with SessionFactory() as db:
        await maintenance(db)
        for event in events:
            extra = {key: value for key, value in event.items() if key != "event_id"}
            db.add(
                UsageEvent(
                    practice_id=practice_id,
                    user_id=person,
                    role=role,
                    client_event_id=str(uuid4()),
                    created_at=utcnow() - timedelta(days=days_ago),
                    **extra,
                )
            )
        await db.commit()


def _review(seconds: int, first: int, keys: int, pointers: int, by_key: int, *, outcome: str = "completed") -> dict:
    return task(
        duration_ms=seconds * 1000,
        first_decision_ms=first * 1000,
        key_inputs=keys,
        pointer_inputs=pointers,
        key_decisions=by_key,
        pointer_decisions=2 - by_key,
        outcome=outcome,
    )


async def _seeded_practice(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    reviews = (_review(10, 2, 10, 0, 2), _review(20, 4, 4, 2, 1), _review(40, 6, 0, 4, 0, outcome="left"))
    await _seed(practice.id, CODER, "coder", *reviews, stall(duration_ms=60_000), stall(duration_ms=90_000))
    upload = task(task="upload", duration_ms=30_000, first_decision_ms=None, key_decisions=0, pointer_decisions=0)
    await _seed(practice.id, ADMIN, "admin", upload)
    await _seed(practice.id, CODER, "coder", task(duration_ms=1_000_000), days_ago=30)
    return practice


async def test_an_admin_sees_medians_and_spread_by_role_and_step_without_names(harness):
    practice = await _seeded_practice(harness)

    figures = await harness.client.get("/api/insights/usage", headers=practice.admin, params={"days": 7})

    assert figures.status_code == 200, figures.text
    body = figures.json()
    assert body["days"] == 7
    review, upload = body["tasks"]
    assert review == {
        "task": "note_review",
        "role": "coder",
        "tasks": 3,
        "completed": 2,
        "people": 1,
        "duration": {"p25": 15.0, "median": 20.0, "p75": 30.0},
        "first_decision": {"p25": 3.0, "median": 4.0, "p75": 5.0},
        "decided": 6,
        "inputs_per_decision": {"p25": 2.5, "median": 3.0, "p75": 4.0},
        "keyboard_share": 0.5,
    }
    assert (upload["task"], upload["role"], upload["tasks"], upload["duration"]) == (
        "upload",
        "admin",
        1,
        {"p25": 30.0, "median": 30.0, "p75": 30.0},
    )
    assert (upload["first_decision"], upload["inputs_per_decision"], upload["keyboard_share"]) == (None, None, None)
    assert body["stalls"] == [
        {
            "task": "note_review",
            "step": "findings",
            "role": "coder",
            "stalls": 2,
            "people": 1,
            "duration": {"p25": 67.5, "median": 75.0, "p75": 82.5},
        }
    ]
    assert CODER not in figures.text and "Sam Patel" not in figures.text


async def test_only_admins_read_the_figures_and_the_period_is_one_of_the_insight_periods(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    coder = await signed_in(harness, CODER)

    refused = await harness.client.get("/api/insights/usage", headers=coder.headers)
    odd = await harness.client.get("/api/insights/usage", headers=practice.admin, params={"days": 5})

    assert (refused.status_code, refused.json()["message"]) == (403, "your role cannot do this")
    assert (odd.status_code, odd.json()["message"]) == (422, "days must be one of 7, 14, 30, 90")


async def test_hq_sees_aggregates_across_practices_and_practices_see_only_their_own(harness):
    lakeside = await _seeded_practice(harness)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")
    await _seed(riverbend.id, "admin@riverbend.example.com", "admin", task(task="queue", **_no_decisions()))
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)

    across = (await harness.client.get("/api/hq/usage", headers=hq)).json()
    own = (await harness.client.get("/api/insights/usage", headers=riverbend.admin)).json()
    refused = await harness.client.get("/api/hq/usage", headers=lakeside.admin)

    assert across["practices"] == 2
    assert [(row["task"], row["role"], row["tasks"]) for row in across["tasks"]] == [
        ("note_review", "coder", 3),
        ("queue", "admin", 1),
        ("upload", "admin", 1),
    ]
    assert [(row["task"], row["tasks"]) for row in own["tasks"]] == [("queue", 1)]
    assert own["stalls"] == []
    assert refused.status_code == 403


def _no_decisions() -> dict[str, Any]:
    return {"duration_ms": 12_000, "first_decision_ms": None, "key_decisions": 0, "pointer_decisions": 0}
