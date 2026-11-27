from __future__ import annotations

from app.services.day_checks import (
    CLONED_TEXT,
    HIGH_LEVEL_SHARE,
    TIME_OVER_DAY,
    DayNote,
    day_flags,
    day_summary,
    jaccard,
    near_duplicates,
    note_body,
    shingles,
)


def test_shingles_are_five_character_windows():
    assert shingles("abcdefg") == frozenset({"abcde", "bcdef", "cdefg"})
    assert shingles("abcd") == frozenset()


def test_jaccard_is_shared_over_combined_shingles():
    assert jaccard(shingles("abcdefg"), shingles("abcdefh")) == 2 / 4
    assert jaccard(frozenset(), frozenset()) == 0.0


def test_the_first_and_last_three_lines_are_left_out_and_spacing_is_ignored():
    text = "Header one\nHeader two\n\nHeader three\nBody   Line\n  second line \nFooter one\nFooter two\nFooter three"
    assert note_body(text) == "body line second line"
    assert note_body("one\ntwo\nthree\nfour\nfive\nsix") == ""


def test_notes_that_differ_only_in_header_and_footer_are_near_duplicates():
    body = "Assessment: stable chronic kidney disease.\nPlan: repeat the panel in three months."
    first = f"Clinic\nPatient Ana\nDate 1\n{body}\nSigned\nClinic\nPage 1"
    second = f"Clinic\nPatient Ben\nDate 2\n{body}\nSigned by another\nClinic two\nPage 9"
    other = "Clinic\nPatient Cy\nDate 3\nKnee pain after a fall.\nIce and rest.\nSigned\nClinic\nPage 1"
    compared, pairs = near_duplicates({"a": first, "b": second, "c": other, "d": "too short"})
    assert compared == 3
    assert pairs == [{"first": "a", "second": "b", "similarity": 1.0}]


def test_flags_follow_the_day_limits():
    assert day_flags(16 * 60, 0.6, 5, 0) == []
    assert day_flags(16 * 60 + 1, 0.61, 5, 1) == [TIME_OVER_DAY, CLONED_TEXT, HIGH_LEVEL_SHARE]
    assert day_flags(0, 1.0, 4, 0) == []


def test_the_high_level_share_counts_the_two_highest_levels_of_each_family():
    notes = [
        DayNote("1", None, "ready", "coder", "99215", 40),
        DayNote("2", None, "ready", "coder", "99205", None),
        DayNote("3", None, "ready", "coder", "99310", 30),
        DayNote("4", None, "ready", "coder", "99213", 20),
        DayNote("5", None, "ready", "coder", "99291", 60),
        DayNote("6", None, "ready", "coder", None, None),
    ]
    summary = day_summary(notes, {})
    assert (summary["visits"], summary["high_level_visits"], summary["high_level_share"]) == (4, 3, 0.75)
    assert (summary["total_minutes"], summary["timed_notes"]) == (150, 4)
    assert summary["flags"] == []
