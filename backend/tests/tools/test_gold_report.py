from __future__ import annotations

from gold_cases import load_gold_set
from gold_report import case_results, group_summaries, report_markdown

RUN = {
    "id": "run-1",
    "status": "done",
    "model": "gemini-test",
    "prompt_version": "2026.11.6",
    "requested_at": "2026-11-30T10:00:00+00:00",
    "finished_at": "2026-11-30T10:40:00+00:00",
}
SAME = {
    "em": {"reference": "x", "compared": "x", "match": True, "direction": "match"},
    "icd": {"matched": 1, "compared": 1, "reference": 1, "missing": [], "extra": [], "match": True},
    "modifiers": {"reference": [], "compared": [], "match": True},
}


def agreement(em: tuple, icd: tuple, modifiers: tuple) -> dict:
    expected, suggested, direction = em
    matched, compared, extra = icd
    return {
        "em": {"reference": expected, "compared": suggested, "match": expected == suggested, "direction": direction},
        "icd": {
            "matched": matched,
            "compared": compared,
            "reference": 1,
            "missing": [],
            "extra": extra,
            "match": not extra,
        },
        "modifiers": {"reference": modifiers[0], "compared": modifiers[1], "match": modifiers[0] == modifiers[1]},
    }


def lines(procedures: tuple, add_ons: tuple, units: tuple) -> dict:
    shared_reference, shared_compared = units
    differing = [code for code in shared_reference if shared_reference[code] != shared_compared[code]]
    return {
        "procedures": {
            "reference": procedures[0],
            "compared": procedures[1],
            "match": procedures[0] == procedures[1],
            "scored": bool(procedures[0] or procedures[1]),
        },
        "add_ons": {
            "reference": add_ons[0],
            "compared": add_ons[1],
            "match": add_ons[0] == add_ons[1],
            "scored": bool(add_ons[0] or add_ons[1]),
        },
        "units": {
            "reference": shared_reference,
            "compared": shared_compared,
            "differing": differing,
            "match": not differing,
            "scored": bool(shared_reference),
        },
        "place_of_service": {"reference": "11", "compared": "11", "match": True, "scored": True},
    }


def results() -> list[dict]:
    return [
        {
            "note_id": "n26",
            "agreement": agreement(("", "99213", "absent"), (1, 1, []), (["LT"], ["25", "LT"])),
            "repeat": SAME,
            "lines": lines((["20610"], ["20610"]), ([], []), ({"20610": 1}, {"20610": 1})),
        },
        {
            "note_id": "n2",
            "agreement": agreement(("99203", "99204", "higher"), (1, 2, ["J06.9"]), ([], [])),
            "repeat": SAME,
            "lines": lines(([], []), ([], ["G2211"]), ({}, {})),
        },
        {"note_id": "n1", "agreement": agreement(("99202", "99202", "match"), (1, 1, []), ([], [])), "repeat": SAME},
        {"note_id": "n3", "error": "model down"},
        {"note_id": "not-in-the-gold-set", "error": "ignored"},
    ]


def rows():
    gold = load_gold_set()
    notes = {"n1": "GS-01", "n2": "GS-02", "n3": "GS-03", "n26": "GS-26"}
    return case_results(results(), {note: gold.case(case_id) for note, case_id in notes.items()})


def test_results_are_matched_to_gold_cases_by_note_and_others_left_out():
    assert [row.case.id for row in rows()] == ["GS-01", "GS-02", "GS-03", "GS-26"]
    assert [row.scored for row in rows()] == [True, True, False, True]


def test_groups_count_cases_and_score_only_the_scored_ones():
    summaries = {label: (count, item) for label, count, item in group_summaries(rows())}
    count, overall = summaries["All gold set cases"]
    assert (count, overall["em"]["successes"], overall["em"]["trials"]) == (4, 1, 3)
    count, expressible = summaries["Cases Bodha's claim can express"]
    assert (count, expressible["em"]["successes"], expressible["em"]["trials"]) == (3, 1, 2)
    assert summaries["Billed one level too high"][0] == 2


def test_the_report_is_provisional_and_states_rates_with_wilson_intervals():
    text = report_markdown(RUN, rows(), load_gold_set())
    assert text.startswith("# Bodha Assure accuracy on the synthetic gold set\n\n**Provisional.**")
    assert "| E/M exact | 33.3% | 6.1% to 79.2% | 1 / 3 |" in text
    assert "| ICD-10-CM exact set | 66.7% | 20.8% to 93.9% | 2 / 3 |" in text
    assert "| Modifiers exact | 66.7% | 20.8% to 93.9% | 2 / 3 |" in text
    assert "| Gold set cases in the run | 4 of 48; 3 scored, 1 failed |" in text
    assert "| Procedure lines exact | 100.0% | 20.7% to 100.0% | 1 / 1 |" in text
    assert "| Add-on codes exact (G2211, G2212, 99417) | 0.0% | 0.0% to 79.3% | 0 / 1 |" in text
    assert "| Units on shared lines | 100.0% | 20.7% to 100.0% | 1 / 1 |" in text
    assert "| Place of service | 100.0% | 34.2% to 100.0% | 2 / 2 |" in text
    assert "Visit codes as billed: 21 billed correctly, 16 one level too high, 8 one level too low" in text


def test_the_report_lists_each_disagreement_and_each_unscored_case():
    text = report_markdown(RUN, rows(), load_gold_set())
    assert "| GS-02 | 99203 | 99204 (higher) |  | J06.9 | none | none |" in text
    assert "| GS-26 | none | 99213 (absent) |  |  | LT | 25, LT |" in text
    assert "- GS-03: model down" in text
    assert "GS-01 |" not in text.split("## Disagreements")[1]


def test_the_report_lists_claim_line_disagreements_and_leaves_out_cases_without_claim_lines():
    text = report_markdown(RUN, rows(), load_gold_set())
    section = text.split("## Claim line disagreements")[1].split("##")[0]
    assert "| GS-02 | none | none | none | G2211 |  |  |" in section
    assert "GS-26" not in section and "GS-01" not in section


def test_a_run_before_claim_line_scoring_shows_those_metrics_with_no_trials():
    older = [{key: value for key, value in row.result.items() if key != "lines"} for row in rows()]
    gold = load_gold_set()
    notes = {"n1": "GS-01", "n2": "GS-02", "n3": "GS-03", "n26": "GS-26"}
    text = report_markdown(RUN, case_results(older, {note: gold.case(case) for note, case in notes.items()}), gold)
    assert "| Procedure lines exact | n/a |  | 0 / 0 |" in text
    assert "## Claim line disagreements" not in text
