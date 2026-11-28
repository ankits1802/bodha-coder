from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.models import Practice
from app.services.payers import payer_list
from app.services.upload_matching import CHECK_BELOW, NOTHING, Matched

__all__ = [
    "LABELLED_PAYER",
    "LABELLED_PLAN",
    "MEMBER_ID_PLAN",
    "UNLABELLED_PAYER",
    "PayerRef",
    "confident_payer",
    "payer_in",
    "payer_refs",
]

LABELLED_PAYER = 0.9
MEMBER_ID_PLAN = 0.85
LABELLED_PLAN = 0.7
UNLABELLED_PAYER = 0.6
WORDS_AFTER_LABEL = 8
LABEL_REACH = 120
MBI_LOOKBEHIND = 32
MBI_LETTER = "AC-HJKMNP-RT-Y"
PAYER_LABEL = re.compile(
    r"\b(?:insurance|insurer|payer|payor|coverage|carrier|health\s+plan|plan\s+name)\b\s*[:#-]?\s*",
    re.IGNORECASE,
)
MBI = re.compile(
    rf"(?<![A-Za-z0-9-])[1-9][{MBI_LETTER}][{MBI_LETTER}0-9][0-9]-?[{MBI_LETTER}][{MBI_LETTER}0-9][0-9]-?"
    rf"[{MBI_LETTER}]{{2}}[0-9]{{2}}(?![A-Za-z0-9-])"
)
MBI_LABEL = re.compile(r"\b(?:mbi|medicare|beneficiary|member)\b", re.IGNORECASE)
MEDICAID_ID = re.compile(r"\bmedicaid\s+(?:member\s+)?(?:id|number|no|#)\s*[:#.]?\s*[A-Za-z0-9]{6,14}\b", re.IGNORECASE)
WORD = re.compile(r"[a-z0-9]+")
PLAN_WORDS: tuple[tuple[str, frozenset[str]], ...] = (
    ("medicare_advantage", frozenset({"medicare", "advantage"})),
    ("medicare", frozenset({"medicare"})),
    ("medicaid", frozenset({"medicaid"})),
)


@dataclass(frozen=True)
class PayerRef:
    id: str
    name: str
    plan_type: str


def payer_refs(practice: Practice) -> list[PayerRef]:
    return [
        PayerRef(payer["id"], payer["name"], payer.get("plan_type") or "")
        for payer in payer_list(practice)
        if payer.get("active")
    ]


def payer_in(text: str, payers: Sequence[PayerRef]) -> Matched[str]:
    flat = " ".join(text.split())
    after_labels = [
        _words(flat[label.end() : label.end() + LABEL_REACH])[:WORDS_AFTER_LABEL]
        for label in PAYER_LABEL.finditer(flat)
    ]
    named = next((found for words in after_labels if (found := _named(words, payers))), None)
    if named:
        return Matched(named, LABELLED_PAYER)
    by_member_id = _only_of_plan(payers, _member_id_plan(flat))
    if by_member_id:
        return Matched(by_member_id, MEMBER_ID_PLAN)
    by_plan = next((found for words in after_labels if (found := _only_of_plan(payers, _plan_named(words)))), None)
    if by_plan:
        return Matched(by_plan, LABELLED_PLAN)
    anywhere = _named(_words(flat), payers)
    return Matched(anywhere, UNLABELLED_PAYER) if anywhere else NOTHING


def confident_payer(match: Matched[str]) -> str | None:
    return match.value if match.confidence >= CHECK_BELOW else None


def _words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def _named(words: list[str], payers: Sequence[PayerRef]) -> str | None:
    found = [(len(name), payer.id) for payer in payers if (name := _words(payer.name)) and _holds(words, name)]
    if not found:
        return None
    longest = max(size for size, _ in found)
    named = {payer_id for size, payer_id in found if size == longest}
    return named.pop() if len(named) == 1 else None


def _holds(words: list[str], name: list[str]) -> bool:
    return any(words[at : at + len(name)] == name for at in range(len(words) - len(name) + 1))


def _member_id_plan(text: str) -> str | None:
    for found in MBI.finditer(text):
        if MBI_LABEL.search(text[max(0, found.start() - MBI_LOOKBEHIND) : found.start()]):
            return "medicare"
    return "medicaid" if MEDICAID_ID.search(text) else None


def _plan_named(words: list[str]) -> str | None:
    present = set(words)
    return next((plan for plan, needed in PLAN_WORDS if needed <= present), None)


def _only_of_plan(payers: Sequence[PayerRef], plan_type: str | None) -> str | None:
    if plan_type is None:
        return None
    matching = [payer.id for payer in payers if payer.plan_type == plan_type]
    return matching[0] if len(matching) == 1 else None
