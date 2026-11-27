from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.ai.contracts import EmReview, ModelClient, ReviewInputs, ReviewOutcome, ReviewReport
from app.core.config import get_settings
from app.worker import process_one
from tests.batches import NoteFile, lines_pdf, note_ids_by_file, upload_batch
from tests.builders import analysis_deps, practice_with_provider

BUSY_DAY = date(2026, 11, 25)
QUIET_DAY = date(2026, 11, 24)
FOOTER = ["Electronically signed by Elena Varga, MD", "Lakeside Internal Medicine", "Page 1 of 1"]
CLONED_BODY = [
    "Chief complaint: follow-up of hypertension and type 2 diabetes mellitus.",
    "History: reports good adherence to metformin and lisinopril, no hypoglycemia.",
    "Exam: lungs clear, heart regular, no edema, monofilament sensation intact in both feet.",
    "Assessment: hypertension at goal and diabetes controlled with an A1c of 6.9 percent.",
    "Plan: continue current medicines and repeat a basic metabolic panel in three months.",
]
OTHER_BODIES = {
    "C": [
        "Acute visit for cough for five days with low grade fever.",
        "Exam shows wheeze on the left base.",
        "Chest film ordered, started on azithromycin.",
        "Return if breathing worsens.",
    ],
    "D": [
        "Knee pain after a fall on ice two weeks ago.",
        "Swelling has improved and range of motion is full.",
        "No laxity on drawer testing.",
        "Ice, ibuprofen as needed and physical therapy referral.",
    ],
    "E": [
        "Annual medication review for hypothyroidism.",
        "TSH 2.1 on levothyroxine 75 micrograms daily.",
        "No palpitations, weight stable.",
        "Continue the same dose and check TSH next year.",
    ],
}
MINUTES = {"A": 300, "B": 300, "C": 200, "D": 100, "E": 100}
BILLED = {"A": "99215", "B": "99215", "C": "99214", "D": "99214", "E": "99213"}


@dataclass
class TimedReviewer:
    minutes: dict[str, int]
    calls: list[ReviewInputs] = field(default_factory=list)

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        self.calls.append(inputs)
        marker = next(key for key in self.minutes if f"Visit marker {key}." in (inputs.note_text or ""))
        em = EmReview(code="99214", basis="Time", time_minutes=self.minutes[marker], justification="Time documented.")
        return ReviewOutcome(report=ReviewReport(em=em), prompt_version="test")


def _note(marker: str, patient: str, body: list[str], *, day: date = BUSY_DAY, billed: str | None = None) -> NoteFile:
    header = ["Lakeside Internal Medicine progress note", f"Patient: {patient}", f"Visit marker {marker}."]
    code = billed or BILLED[marker]
    return NoteFile(
        f"{day.isoformat()} - {patient} - {code} - Progress.pdf", lines_pdf([*header, *body, *FOOTER]), code
    )


async def _read_all(harness, icd_catalog, count: int, minutes: dict[str, int]) -> None:
    deps = analysis_deps(harness, icd_catalog, TimedReviewer(minutes))
    for _ in range(count):
        assert await process_one(deps, get_settings()) is True


async def _busy_and_quiet_days(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    patients = {"A": "Ana Diaz", "B": "Ben Cole", "C": "Cara Lim", "D": "Dev Rao", "E": "Eva Moss"}
    files = [_note(key, patients[key], CLONED_BODY if key in "AB" else OTHER_BODIES[key]) for key in "ABCDE"]
    await upload_batch(harness, practice, practice.provider_id, BUSY_DAY, files)
    quiet = [_note(key, f"Quiet {key}", OTHER_BODIES[key], day=QUIET_DAY, billed="99213") for key in "CD"]
    await upload_batch(harness, practice, practice.provider_id, QUIET_DAY, quiet)
    await _read_all(harness, icd_catalog, 7, MINUTES)
    ids = await note_ids_by_file(harness, practice)
    return practice, {key: ids[files[index].name] for index, key in enumerate("ABCDE")}


async def test_a_day_with_too_much_time_cloned_text_and_high_levels_is_flagged(harness, icd_catalog):
    practice, ids = await _busy_and_quiet_days(harness, icd_catalog)

    response = await harness.client.get(f"/api/notes/{ids['C']}/day", headers=practice.admin)

    assert response.status_code == 200, response.text
    day = response.json()
    assert (day["note_id"], day["service_date"], day["provider"]["name"]) == (ids["C"], "2026-11-25", "Elena Varga")
    assert sorted(note["id"] for note in day["notes"]) == sorted(ids.values())
    assert (day["total_minutes"], day["timed_notes"]) == (1000, 5)
    assert day["levels"] == [
        {"code": "99213", "count": 1},
        {"code": "99214", "count": 2},
        {"code": "99215", "count": 2},
    ]
    assert (day["visits"], day["high_level_visits"], day["high_level_share"]) == (5, 4, 0.8)
    assert day["compared"] == 5
    assert [({pair["first"], pair["second"]}, pair["similarity"]) for pair in day["duplicates"]] == [
        ({ids["A"], ids["B"]}, 1.0)
    ]
    assert day["flags"] == ["time_over_day", "cloned_text", "high_level_share"]


async def test_the_compliance_list_shows_only_flagged_provider_days(harness, icd_catalog):
    practice, ids = await _busy_and_quiet_days(harness, icd_catalog)

    response = await harness.client.get(
        "/api/compliance/days", headers=practice.admin, params={"from": "2026-11-01", "to": "2026-11-30"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["from"], body["to"]) == ("2026-11-01", "2026-11-30")
    assert [(day["service_date"], day["provider"]["name"], day["flags"]) for day in body["days"]] == [
        ("2026-11-25", "Elena Varga", ["time_over_day", "cloned_text", "high_level_share"])
    ]
    actions = [
        row["action"] for row in (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    ]
    assert "listed provider days" in actions


async def test_a_date_range_must_run_forwards_and_stay_within_a_quarter(harness):
    practice = await practice_with_provider(harness)
    backwards = {"from": "2026-11-30", "to": "2026-11-01"}
    too_long = {"from": "2026-01-01", "to": "2026-11-30"}
    for params in (backwards, too_long):
        response = await harness.client.get("/api/compliance/days", headers=practice.admin, params=params)
        assert response.status_code == 422, response.text
