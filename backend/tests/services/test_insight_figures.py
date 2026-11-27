from datetime import UTC, date, datetime, timedelta

from app.codes.billing_codes import parse_code_list
from app.services.insights import ApprovedNote, coder_productivity, estimated_differences

READY = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)


def _note(
    note_id: str,
    *,
    approver: str = "Ana Ruiz",
    provider: str = "Elena Varga",
    billed: str = "99215, I10",
    final: str = "99215, I10",
    place: str = "11",
    minutes: float | None = 10,
    service_date: date = date(2026, 11, 25),
) -> ApprovedNote:
    approved_at = READY + timedelta(minutes=minutes if minutes is not None else 5)
    return ApprovedNote(
        note_id=note_id,
        provider_name=provider,
        approver_id=approver.lower(),
        approver_name=approver,
        place_code=place,
        service_date=service_date,
        ready_at=READY if minutes is not None else None,
        approved_at=approved_at,
        final=parse_code_list(final).codes,
        billed=parse_code_list(billed).codes,
    )


def test_each_person_has_approvals_median_wait_and_changes():
    notes = [
        _note("a", minutes=10),
        _note("b", minutes=30, final="99214, I10"),
        _note("c", minutes=20),
        _note("d", approver="Ben Okafor", minutes=None),
    ]

    assert coder_productivity(notes) == [
        {"id": "ana ruiz", "name": "Ana Ruiz", "approved": 3, "median_minutes": 20.0, "changed": 1},
        {"id": "ben okafor", "name": "Ben Okafor", "approved": 1, "median_minutes": None, "changed": 0},
    ]


def test_an_even_count_takes_the_middle_two():
    notes = [_note("a", minutes=4), _note("b", minutes=6), _note("c", minutes=9), _note("d", minutes=13)]
    assert coder_productivity(notes)[0]["median_minutes"] == 7.5


def test_estimated_differences_add_up_per_provider():
    notes = [
        _note("a", billed="99215, I10", final="99214, I10"),
        _note("b", billed="99213, I10", final="99214, I10"),
        _note("c", provider="Omar Haddad", billed="99232", final="99232", place="21"),
        _note("d", provider="Omar Haddad", billed="99215", final="99214", service_date=date(2025, 12, 1)),
    ]

    figures = estimated_differences(notes)

    assert figures["notes"] == 3
    assert figures["difference"] == -16.36
    assert figures["providers"] == [
        {"provider_name": "Elena Varga", "notes": 2, "difference": -16.36},
        {"provider_name": "Omar Haddad", "notes": 1, "difference": 0.0},
    ]


def test_an_added_screening_counts_its_units():
    figures = estimated_differences([_note("a", billed="99214", final="99214, 96127x2")])
    assert figures["difference"] == 10.02
