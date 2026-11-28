from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from gold_api import ENV_PRACTICE, ApiError, BodhaApi, Credentials, SetupError
from gold_cases import PAYER_NAMES, GoldCase, GoldSet

from app.codes.billing_codes import Code, parse_code_list

__all__ = [
    "CONFIRM_REASON",
    "OVERRIDE_REASON",
    "LoadContext",
    "LoadError",
    "Outcome",
    "Practice",
    "StillReading",
    "Waiting",
    "all_loaded",
    "check_practice",
    "claim_key",
    "find_note",
    "load_cases",
    "preflight",
    "rejecting_decisions",
    "summary_lines",
]

OVERRIDE_REASON = "coding_guideline"
CONFIRM_REASON = "Synthetic evaluation case; the expected claim was set by construction."
SETTLED = ("approved", "exported")
READING = ("queued", "reading")
VOIDED = "voided"
ACCEPTING = ("accept", "add")
REJECTING = ("keep", "skip")
LOADED, ALREADY, FAILED, WAITING = "loaded", "already loaded", "failed", "still reading"

ClaimKey = frozenset[tuple[str, str, tuple[str, ...], int]]


class LoadError(RuntimeError):
    pass


class StillReading(LoadError):
    pass


@dataclass(frozen=True)
class Outcome:
    case_id: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class Waiting:
    sleep: Callable[[float], None]
    clock: Callable[[], float]
    poll_seconds: float
    timeout_seconds: float


@dataclass
class Practice:
    provider_ids: Mapping[str, str]
    marked: set[str] = field(default_factory=set)
    payer_ids: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadContext:
    api: BodhaApi
    gold: GoldSet
    practice: Practice
    waiting: Waiting
    render: Callable[[GoldCase], bytes]
    say: Callable[[str], None]


def check_practice(api: BodhaApi, credentials: Credentials) -> None:
    user = api.get("/api/auth/me")
    if (user.get("practice") or {}).get("id") != credentials.practice_id:
        raise SetupError(f"the account is not signed in to the evaluation practice named by {ENV_PRACTICE}")
    if user.get("role") != "admin":
        raise SetupError("the evaluation account must be an admin of the evaluation practice")


def preflight(api: BodhaApi, gold: GoldSet, credentials: Credentials) -> Practice:
    check_practice(api, credentials)
    if api.get("/api/signature").get("signature") is None:
        raise SetupError("adopt a signature for this account in the app before approving notes")
    if api.get("/api/practice/setup")["review"]["confirm_level_changes"]:
        raise SetupError("turn off level confirmation in the evaluation practice so approvals send nothing")
    active = {row["code"] for row in api.get("/api/places")}
    missing = sorted({case.visit.place_of_service for case in gold.cases} - active)
    if missing:
        raise SetupError(f"places of service {missing} are not active")
    marked = {row["note_id"] for row in api.get("/api/quality/eval-cases")["items"]}
    return Practice(_provider_ids(api, gold), marked, _payer_ids(api, gold))


def load_cases(context: LoadContext, cases: Iterable[GoldCase]) -> list[Outcome]:
    chosen = list(cases)
    outcomes: dict[str, Outcome] = {}
    for case in chosen:
        try:
            _ensure_uploaded(context, case)
        except (LoadError, ApiError) as error:
            outcomes[case.id] = _failure(case, error)
            context.say(_line(outcomes[case.id]))
    for case in [case for case in chosen if case.id not in outcomes]:
        try:
            outcomes[case.id] = _load_case(context, case)
        except (LoadError, ApiError) as error:
            outcomes[case.id] = _failure(case, error)
        context.say(_line(outcomes[case.id]))
    return [outcomes[case.id] for case in chosen]


def claim_key(codes: Iterable[Code]) -> ClaimKey:
    return frozenset((code.type, code.code, tuple(sorted(code.modifiers)), code.units) for code in codes)


def rejecting_decisions(findings: Iterable[Mapping[str, Any]], reason: Mapping[str, str]) -> dict[str, Any] | None:
    choices: dict[str, str] = {}
    reasons: dict[str, Mapping[str, str]] = {}
    for finding in findings:
        if finding["choice"] not in ACCEPTING:
            continue
        choice = next((option for option in REJECTING if option in finding["allowed"]), None)
        if choice is None:
            raise LoadError(f"suggestion {finding['key']} cannot be turned down")
        choices[finding["key"]] = choice
        if choice in finding["departing_choices"]:
            reasons[finding["key"]] = reason
    return {"choices": choices, "reasons": reasons} if choices else None


def all_loaded(outcomes: Iterable[Outcome]) -> bool:
    return all(outcome.status in (LOADED, ALREADY) for outcome in outcomes)


def summary_lines(outcomes: Iterable[Outcome]) -> list[str]:
    listed = list(outcomes)
    counts = {status: sum(item.status == status for item in listed) for status in (LOADED, ALREADY, WAITING, FAILED)}
    lines = [", ".join(f"{count} {status}" for status, count in counts.items())]
    lines += [_line(item) for item in listed if item.status in (WAITING, FAILED)]
    return lines


def _provider_ids(api: BodhaApi, gold: GoldSet) -> dict[str, str]:
    listed = {(row["name"], row["credential"]): row for row in api.get("/api/providers")}
    found: dict[str, str] = {}
    for provider in gold.providers.values():
        row = listed.get((provider.name, provider.credential))
        if row is not None and not row["active"]:
            raise SetupError(f"provider {provider.signature} is inactive in the evaluation practice")
        if row is None:
            body = {"name": provider.name, "credential": provider.credential}
            body |= {"specialty": provider.specialty, "email": provider.email}
            row = api.post("/api/providers", json=body)
        found[provider.key] = row["id"]
    return found


def _payer_ids(api: BodhaApi, gold: GoldSet) -> dict[str, str]:
    listed = {(row["name"], row["plan_type"]): row["id"] for row in api.get("/api/payers")}
    found: dict[str, str] = {}
    for plan in sorted({case.visit.payer for case in gold.cases}):
        name = PAYER_NAMES[plan]
        payer_id = listed.get((name, plan))
        if payer_id is None:
            payer_id = api.post("/api/practice/payers", json={"name": name, "plan_type": plan})["id"]
        found[plan] = payer_id
    return found


def _failure(case: GoldCase, error: Exception) -> Outcome:
    return Outcome(case.id, WAITING if isinstance(error, StillReading) else FAILED, str(error))


def _ensure_uploaded(context: LoadContext, case: GoldCase) -> None:
    if find_note(context.api, case) is not None:
        return
    provider_id = context.practice.provider_ids[case.visit.provider]
    detail = {"billed": case.billed_text, "visit_type": case.visit.visit_type, "provider_id": provider_id}
    detail |= {"service_date": case.visit.service_date.isoformat(), "place_code": case.visit.place_of_service}
    detail |= {"payer": context.practice.payer_ids[case.visit.payer]}
    form = {"visit_type": case.visit.visit_type, "details": json.dumps([detail])}
    files = [("files", (case.file_name, context.render(case), "application/pdf"))]
    result = context.api.upload("/api/uploads", form, files)
    if case.file_name in result.get("duplicates", []) and find_note(context.api, case) is None:
        raise LoadError("the same PDF is already in the practice under another file name")
    context.say(f"{case.id}: uploaded")


def _load_case(context: LoadContext, case: GoldCase) -> Outcome:
    note = find_note(context.api, case)
    if note is None:
        raise LoadError("the note was not found after upload")
    detail = _read(context, note["id"])
    if detail["note"]["status"] in SETTLED:
        return _finish_settled(context, case, detail)
    _ensure_payer(context, case, detail["note"])
    detail = _settle(context.api, case, detail)
    _approve(context.api, detail)
    _mark(context, note["id"])
    return Outcome(case.id, LOADED, "approved and marked as an evaluation case")


def find_note(api: BodhaApi, case: GoldCase) -> dict[str, Any] | None:
    rows = api.get("/api/search", params={"q": case.id})["items"]
    named = [row for row in rows if row["file_name"] == case.file_name and row["status"] != VOIDED]
    if len(named) > 1:
        raise LoadError(f"{len(named)} notes are named {case.file_name}; void the extra ones in the app")
    return named[0] if named else None


def _read(context: LoadContext, note_id: str) -> dict[str, Any]:
    deadline = context.waiting.clock() + context.waiting.timeout_seconds
    retried = False
    while True:
        detail = context.api.get(f"/api/notes/{note_id}")
        status = detail["note"]["status"]
        if status == "failed" and retried:
            raise LoadError(f"Bodha could not read the note: {detail.get('failure')}")
        if status == "failed":
            context.api.post(f"/api/notes/{note_id}/retry")
            retried = True
        elif status not in READING:
            return detail
        if context.waiting.clock() >= deadline:
            raise StillReading("Bodha's review is not finished yet; run the loader again later")
        context.waiting.sleep(context.waiting.poll_seconds)


def _ensure_payer(context: LoadContext, case: GoldCase, note: Mapping[str, Any]) -> None:
    payer = context.practice.payer_ids[case.visit.payer]
    if note.get("payer") != payer:
        context.api.put(f"/api/notes/{note['id']}/payer", {"payer": payer})


def _settle(api: BodhaApi, case: GoldCase, detail: dict[str, Any]) -> dict[str, Any]:
    expected = claim_key(case.expected)
    if _current_claim(detail) == expected:
        return _unblocked(detail)
    note_id = detail["note"]["id"]
    reason = _override(case)
    billed = _latest_codes(detail, "billed")
    if billed is None or claim_key(billed) != expected:
        detail = api.put(f"/api/notes/{note_id}/billed-codes", {"codes": case.expected_text, "reason": reason})
    decisions = rejecting_decisions(detail["findings"], reason)
    if decisions is not None:
        detail = api.put(f"/api/notes/{note_id}/decisions", decisions)
    if _current_claim(detail) != expected:
        raise LoadError(f"the claim is {', '.join(detail['claim'])}, expected {case.expected_text}")
    return _unblocked(detail)


def _unblocked(detail: dict[str, Any]) -> dict[str, Any]:
    blocked = [item["code_before"] for item in detail["findings"] if item["action"] == "review" and item["code_before"]]
    if blocked:
        raise LoadError(f"Bodha could not confirm {', '.join(blocked)}; approval needs a person in the app")
    return detail


def _approve(api: BodhaApi, detail: dict[str, Any]) -> None:
    note = detail["note"]
    if note["lane"] == "compliance":
        api.post(f"/api/notes/{note['id']}/compliance", {"decision": "confirm", "reason": CONFIRM_REASON})
    else:
        api.post(f"/api/notes/{note['id']}/approve")


def _finish_settled(context: LoadContext, case: GoldCase, detail: dict[str, Any]) -> Outcome:
    final = _latest_codes(detail, "final")
    if final is None or claim_key(final) != claim_key(case.expected):
        shown = ", ".join(code.label() for code in final or ())
        raise LoadError(f"already approved as {shown or 'nothing'}, not {case.expected_text}; reopen or void it")
    note_id = detail["note"]["id"]
    if note_id in context.practice.marked:
        return Outcome(case.id, ALREADY)
    _mark(context, note_id)
    return Outcome(case.id, LOADED, "marked as an evaluation case")


def _mark(context: LoadContext, note_id: str) -> None:
    if note_id not in context.practice.marked:
        context.api.post("/api/quality/eval-cases", {"note_id": note_id})
        context.practice.marked.add(note_id)


def _current_claim(detail: Mapping[str, Any]) -> ClaimKey:
    parsed = parse_code_list(", ".join(detail["claim"]))
    if parsed.invalid:
        raise LoadError(f"the claim shown has codes this loader cannot read: {', '.join(parsed.invalid)}")
    return claim_key(parsed.codes)


def _latest_codes(detail: Mapping[str, Any], kind: str) -> tuple[Code, ...] | None:
    sets = [item for item in detail["history"]["code_sets"] if item["kind"] == kind]
    if not sets:
        return None
    latest = max(sets, key=lambda item: item["revision"])
    return tuple(Code.from_json(item) for item in latest["codes"])


def _override(case: GoldCase) -> dict[str, str]:
    return {
        "reason": OVERRIDE_REASON,
        "note": f"Synthetic evaluation case {case.id}: expected claim set by construction.",
    }


def _line(outcome: Outcome) -> str:
    return f"{outcome.case_id}: {outcome.status}" + (f" ({outcome.detail})" if outcome.detail else "")
