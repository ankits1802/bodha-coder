from __future__ import annotations

from datetime import date

from tests.api.spend_helpers import UNLISTED, Run, figures, figures_of, hq_headers, record_runs, utc
from tests.batches import NoteFile, add_provider, note_ids_by_file, upload_batch
from tests.builders import FILE_NAME, Harness, practice_with_provider, upload_note
from tests.fakes import NOTE_TEXT, text_pdf

PATH = "/api/hq/expenditure"
NOVEMBER = {"from": "2026-11-01", "to": "2026-11-30"}
HADDAD_FIRST = "haddad first.pdf"
HADDAD_SECOND = "haddad second.pdf"


async def november_spend(harness: Harness) -> tuple[str, str]:
    lakeside = await practice_with_provider(harness)
    haddad = await add_provider(harness, lakeside, name="Omar Haddad", specialty=None)
    await upload_note(harness, lakeside)
    files = [NoteFile(name, text_pdf(f"{NOTE_TEXT} {name}"), "99213") for name in (HADDAD_FIRST, HADDAD_SECOND)]
    await upload_batch(harness, lakeside, haddad, date(2026, 11, 20), files)
    hillside = await practice_with_provider(harness, name="Hillside", admin_email="admin@hillside.example.com")
    await upload_note(harness, hillside)
    lakeside_notes = await note_ids_by_file(harness, lakeside)
    hillside_notes = await note_ids_by_file(harness, hillside)
    await record_runs(
        lakeside_notes[FILE_NAME],
        [
            Run("superseded", utc("2026-11-01T00:00:00"), 1_000_000, 100_000, 800_000),
            Run("succeeded", utc("2026-11-30T23:59:59"), 200_000, 50_000, 250_000),
            Run("failed", utc("2026-11-15T12:00:00"), 20_000, 0, 10_000),
        ],
    )
    await record_runs(
        lakeside_notes[HADDAD_FIRST],
        [
            Run("superseded", utc("2026-11-10T09:00:00"), 30_000, 6_000, None, UNLISTED),
            Run("succeeded", utc("2026-11-12T09:00:00"), 0, 0, None, "demo"),
        ],
    )
    await record_runs(
        lakeside_notes[HADDAD_SECOND],
        [
            Run("superseded", utc("2026-10-31T23:59:59"), 999, 999, 3_497),
            Run("superseded", utc("2026-11-20T09:00:00"), 100_000, 10_000, 80_000),
            Run("succeeded", utc("2026-12-01T00:00:00"), 999, 999, 3_497),
        ],
    )
    await record_runs(
        hillside_notes[FILE_NAME], [Run("succeeded", utc("2026-11-05T09:00:00"), 2_000_000, 0, 1_000_000)]
    )
    return lakeside.id, hillside.id


async def test_hq_sees_what_each_practice_and_provider_cost_over_utc_days(harness):
    lakeside_id, hillside_id = await november_spend(harness)
    report = (await harness.client.get(PATH, headers=await hq_headers(harness), params=NOVEMBER)).json()
    assert (report["from"], report["to"], report["time_zone"]) == ("2026-11-01", "2026-11-30", "UTC")
    assert figures_of(report["totals"]) == figures(6, 4, 3_350_000, 166_000, 2.14, None, 1)
    assert report["unpriced_models"] == [UNLISTED]
    lakeside, hillside = report["practices"]
    assert (lakeside["id"], lakeside["name"], lakeside["plan"], lakeside["plan_monthly_cents"]) == (
        lakeside_id,
        "Lakeside",
        "professional",
        24_900,
    )
    assert figures_of(lakeside) == figures(5, 3, 1_350_000, 166_000, 1.14, None, 1)
    assert [(provider["name"], figures_of(provider)) for provider in lakeside["providers"]] == [
        ("Elena Varga", figures(3, 1, 1_220_000, 150_000, 1.06, 1.06, 0)),
        ("Omar Haddad", figures(2, 2, 130_000, 16_000, 0.08, None, 1)),
    ]
    assert (hillside["id"], figures_of(hillside)) == (hillside_id, figures(1, 1, 2_000_000, 0, 1.0, 1.0, 0))
    assert [provider["name"] for provider in hillside["providers"]] == ["Elena Varga"]


async def test_one_practice_can_be_asked_for_alone(harness):
    _, hillside_id = await november_spend(harness)
    hq = await hq_headers(harness)
    report = (await harness.client.get(PATH, headers=hq, params={**NOVEMBER, "practice_id": hillside_id})).json()
    assert [practice["name"] for practice in report["practices"]] == ["Hillside"]
    assert figures_of(report["totals"]) == figures(1, 1, 2_000_000, 0, 1.0, 1.0, 0)
    assert report["unpriced_models"] == []
    missing = await harness.client.get(PATH, headers=hq, params={**NOVEMBER, "practice_id": "no-such-practice"})
    assert missing.status_code == 404


async def test_a_day_outside_the_range_counts_nothing_and_still_lists_every_practice_at_zero(harness):
    lakeside_id, hillside_id = await november_spend(harness)
    report = (
        await harness.client.get(
            PATH, headers=await hq_headers(harness), params={"from": "2026-12-02", "to": "2026-12-31"}
        )
    ).json()
    assert report["unpriced_models"] == []
    assert figures_of(report["totals"]) == figures(0, 0, 0, 0, 0.0, None, 0)
    assert [(practice["id"], practice["name"], practice["providers"]) for practice in report["practices"]] == [
        (hillside_id, "Hillside", []),
        (lakeside_id, "Lakeside", []),
    ]
    assert all(figures_of(practice) == figures(0, 0, 0, 0, 0.0, None, 0) for practice in report["practices"])


async def test_a_practice_with_no_reads_is_shown_at_zero_rather_than_hidden(harness):
    await november_spend(harness)
    quiet = await practice_with_provider(harness, name="Quiet Creek", admin_email="admin@quiet.example.com")
    hq = await hq_headers(harness)
    everyone = (await harness.client.get(PATH, headers=hq, params=NOVEMBER)).json()
    assert [practice["name"] for practice in everyone["practices"]] == ["Lakeside", "Hillside", "Quiet Creek"]
    alone = (await harness.client.get(PATH, headers=hq, params={**NOVEMBER, "practice_id": quiet.id})).json()
    assert [(practice["id"], practice["plan_monthly_cents"]) for practice in alone["practices"]] == [(quiet.id, 24_900)]
    assert figures_of(alone["practices"][0]) == figures(0, 0, 0, 0, 0.0, None, 0)


async def test_only_hq_reads_spend_and_the_range_must_be_whole(harness):
    lakeside = await practice_with_provider(harness)
    assert (await harness.client.get(PATH, params=NOVEMBER)).status_code == 401
    assert (await harness.client.get(PATH, headers=lakeside.admin, params=NOVEMBER)).status_code == 403
    hq = await hq_headers(harness)
    backwards = await harness.client.get(PATH, headers=hq, params={"from": "2026-11-30", "to": "2026-11-01"})
    assert backwards.status_code == 422
    assert (await harness.client.get(PATH, headers=hq, params={"from": "2026-11-01"})).status_code == 422
    assert (
        await harness.client.get(PATH, headers=hq, params={"from": "2026-11-31", "to": "2026-12-01"})
    ).status_code == 422
