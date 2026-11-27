from app.core.db import SessionFactory
from app.models import Analysis, Note
from app.services.analysis import claim_next
from app.services.job_control import queue_counts, requeue_interrupted
from tests.builders import practice_with_provider, upload_note


async def test_an_interrupted_read_goes_back_to_the_queue_without_using_an_attempt(harness):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    async with SessionFactory() as db:
        assert await queue_counts(db) == (1, 0)
        claimed = await claim_next(db)
        assert (claimed.status, claimed.attempts) == ("running", 1)
        assert await queue_counts(db) == (0, 1)
    async with SessionFactory() as db:
        await requeue_interrupted(db, claimed.id)
    async with SessionFactory() as db:
        analysis = await db.get_one(Analysis, claimed.id)
        note = await db.get_one(Note, analysis.note_id)
        assert (analysis.status, analysis.attempts, note.status) == ("queued", 0, "queued")
        assert await queue_counts(db) == (1, 0)


async def test_requeueing_a_finished_read_changes_nothing(harness):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    async with SessionFactory() as db:
        claimed = await claim_next(db)
        claimed.status = "succeeded"
        await db.commit()
    async with SessionFactory() as db:
        await requeue_interrupted(db, claimed.id)
        assert (await db.get_one(Analysis, claimed.id)).status == "succeeded"
