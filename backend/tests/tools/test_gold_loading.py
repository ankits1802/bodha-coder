from __future__ import annotations

from dataclasses import dataclass

import pytest
from gold_api import ApiError, BodhaApi, Credentials, SetupError
from gold_cases import load_gold_set
from gold_loading import (
    CONFIRM_REASON,
    LoadContext,
    Outcome,
    Waiting,
    load_cases,
    preflight,
    rejecting_decisions,
    summary_lines,
)

from tests.tools.fake_bodha import EMAIL, NOW, PASSWORD, PRACTICE_ID, TOTP_SECRET, FakeBodha, FakeNote

CREDENTIALS = Credentials(EMAIL, PRACTICE_ID, PASSWORD, TOTP_SECRET)
REASON = {"reason": "coding_guideline", "note": "Synthetic evaluation case GS-01: expected claim set by construction."}
GS01_FILE = "2025-10-14 - SYNTHETIC PATIENT - GS-01.pdf"


@dataclass
class FakeClock:
    seconds: float = 0.0

    def now(self) -> float:
        return self.seconds

    def sleep(self, seconds: float) -> None:
        self.seconds += seconds


def run(fake: FakeBodha, case_ids: list[str], lines: list[str] | None = None) -> list[Outcome]:
    gold = load_gold_set()
    api = BodhaApi(fake.client(), clock=lambda: NOW)
    api.sign_in(CREDENTIALS)
    clock = FakeClock()
    said = lines if lines is not None else []
    context = LoadContext(
        api, gold, preflight(api, gold, CREDENTIALS), Waiting(clock.sleep, clock.now, 1.0, 5.0), _pdf, said.append
    )
    return load_cases(context, [gold.case(case_id) for case_id in case_ids])


def _pdf(case) -> bytes:
    return b"%PDF-1.7 synthetic"


def test_a_mis_billed_case_is_uploaded_corrected_approved_and_marked():
    fake = FakeBodha()
    assert run(fake, ["GS-01"]) == [Outcome("GS-01", "loaded", "approved and marked as an evaluation case")]
    assert fake.uploads == [
        {
            "file_name": GS01_FILE,
            "billed": "99203, L23.7",
            "visit_type": "New patient",
            "provider_id": "provider-3",
            "service_date": "2025-10-14",
            "place_code": "11",
        }
    ]
    edits = [body for method, path, body in fake.calls if path.endswith("/billed-codes")]
    assert edits == [{"codes": "99202, L23.7", "reason": REASON}]
    assert (fake.notes["note-1"].final, fake.marked) == (["99202", "L23.7"], {"note-1"})
    assert [provider["name"] for provider in fake.providers][:3] == [
        "Avery Quillfeather",
        "Rowan Tessaly",
        "Sage Marrowind",
    ]


def test_a_claim_bodha_already_gets_right_is_approved_as_it_stands():
    fake = FakeBodha(claim_after_upload=["99202", "L23.7"])
    assert run(fake, ["GS-01"])[0].status == "loaded"
    assert fake.paths("PUT") == []
    assert fake.paths("POST")[-2:] == ["/api/notes/note-1/approve", "/api/quality/eval-cases"]


def test_suggestions_left_after_the_billed_edit_are_turned_down_with_a_reason():
    em = {"key": "em", "choice": "accept", "allowed": ["accept", "keep"], "departing_choices": ["keep"]}
    query = {"key": "q1", "choice": "ask", "allowed": ["ask", "skip"], "departing_choices": []}
    findings = [{**em, "action": "lower", "code_before": "99215"}, {**query, "action": "ask", "code_before": None}]
    fake = FakeBodha(claim_after_upload=["99214", "G2211", "I10"], findings_after_upload=findings)
    assert run(fake, ["GS-17"])[0].status == "loaded"
    reason = {**REASON, "note": REASON["note"].replace("GS-01", "GS-17")}
    decided = [body for method, path, body in fake.calls if path.endswith("/decisions")]
    assert decided == [{"choices": {"em": "keep"}, "reasons": {"em": reason}}]
    assert fake.notes["note-1"].final == ["99214", "G2211", "I10", "E78.5"]


def test_a_departing_choice_carries_a_reason_and_questions_are_left_alone():
    findings = [
        {"key": "em", "choice": "accept", "allowed": ["accept", "keep"], "departing_choices": ["keep"]},
        {"key": "dx:E78.5", "choice": "add", "allowed": ["add", "skip"], "departing_choices": ["skip"]},
        {"key": "q1", "choice": "ask", "allowed": ["ask", "skip"], "departing_choices": []},
        {"key": "risk-1", "choice": "keep", "allowed": ["keep"], "departing_choices": []},
    ]
    assert rejecting_decisions(findings, REASON) == {
        "choices": {"em": "keep", "dx:E78.5": "skip"},
        "reasons": {"em": REASON, "dx:E78.5": REASON},
    }
    assert rejecting_decisions(findings[2:], REASON) is None


def test_a_second_run_skips_a_case_already_loaded():
    fake = FakeBodha(marked={"note-1"})
    fake.notes["note-1"] = FakeNote("note-1", GS01_FILE, ["99203", "L23.7"], ["99202", "L23.7"], "approved")
    fake.notes["note-1"].final = ["99202", "L23.7"]
    assert run(fake, ["GS-01"]) == [Outcome("GS-01", "already loaded")]
    assert "/api/uploads" not in fake.paths("POST") and fake.paths("PUT") == []


def test_a_note_approved_with_another_claim_is_reported_and_not_marked():
    fake = FakeBodha()
    fake.notes["note-1"] = FakeNote("note-1", GS01_FILE, ["99203", "L23.7"], ["99203", "L23.7"], "approved")
    fake.notes["note-1"].final = ["99203", "L23.7"]
    outcome = run(fake, ["GS-01"])[0]
    assert outcome.status == "failed"
    assert outcome.detail == "already approved as 99203, L23.7, not 99202, L23.7; reopen or void it"
    assert fake.marked == set()


def test_a_note_still_being_read_is_left_for_the_next_run():
    fake = FakeBodha(reads_after_upload=100)
    outcome = run(fake, ["GS-01"])[0]
    assert outcome.status == "still reading"
    assert "/api/notes/note-1/approve" not in fake.paths("POST")


def test_a_note_in_the_compliance_lane_is_confirmed_through_compliance():
    fake = FakeBodha(claim_after_upload=["99213", "M1A.9XX0"], lane_after_upload="compliance")
    assert run(fake, ["GS-21"])[0].status == "loaded"
    confirmed = [body for method, path, body in fake.calls if path == "/api/notes/note-1/compliance"]
    assert confirmed == [{"decision": "confirm", "reason": CONFIRM_REASON}]


def test_two_step_sign_in_works_and_no_secret_is_ever_printed():
    lines: list[str] = []
    run(FakeBodha(), ["GS-01"], lines)
    with pytest.raises(ApiError) as refused:
        BodhaApi(FakeBodha().client()).sign_in(Credentials(EMAIL, PRACTICE_ID, "wrong-password-2", TOTP_SECRET))
    printed = "\n".join([*lines, str(refused.value)])
    assert lines == ["GS-01: uploaded", "GS-01: loaded (approved and marked as an evaluation case)"]
    assert PASSWORD not in printed and TOTP_SECRET not in printed and "wrong-password-2" not in printed


def test_credentials_come_from_the_environment_and_stay_out_of_repr():
    with pytest.raises(SetupError, match="BODHA_EVAL_EMAIL, BODHA_EVAL_PASSWORD, BODHA_EVAL_PRACTICE_ID"):
        Credentials.from_environment({})
    environ = {
        "BODHA_EVAL_EMAIL": EMAIL,
        "BODHA_EVAL_PASSWORD": PASSWORD,
        "BODHA_EVAL_PRACTICE_ID": PRACTICE_ID,
        "BODHA_EVAL_TOTP_SECRET": "JBSW Y3DP EHPK 3PXP",
    }
    credentials = Credentials.from_environment(environ)
    assert credentials == CREDENTIALS
    assert PASSWORD not in repr(credentials) and TOTP_SECRET not in repr(credentials)


def test_preflight_refuses_a_practice_other_than_the_evaluation_one():
    fake = FakeBodha(practice_id="practice-real")
    api = BodhaApi(fake.client(), clock=lambda: NOW)
    api.sign_in(CREDENTIALS)
    with pytest.raises(SetupError, match="BODHA_EVAL_PRACTICE_ID"):
        preflight(api, load_gold_set(), CREDENTIALS)
    assert "/api/providers" not in fake.paths("POST")


def test_the_summary_counts_outcomes_and_lists_what_needs_attention():
    outcomes = [Outcome("GS-01", "loaded"), Outcome("GS-02", "already loaded"), Outcome("GS-03", "failed", "boom")]
    assert summary_lines(outcomes) == ["1 loaded, 1 already loaded, 0 still reading, 1 failed", "GS-03: failed (boom)"]
