from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.codes.billing_codes import FilenameFacts
from app.codes.npi import is_valid_npi

__all__ = [
    "CHECK_BELOW",
    "FileMatch",
    "Matched",
    "ProviderRef",
    "match_file",
    "patient_in",
    "place_in",
    "provider_in",
    "service_date_in",
    "text_dates",
]

NPI_MATCH = 0.99
FULL_NAME = 0.9
LAST_NAME_ONLY = 0.6
DATES_AGREE = 0.99
LABELLED_DATE = 0.95
FILE_NAME_DATE = 0.85
DATES_DISAGREE = 0.6
UNLABELLED_DATE = 0.5
LABELLED_PLACE = 0.95
PROVIDER_PLACE = 0.8
LABELLED_PATIENT = 0.9
FILE_NAME_PATIENT = 0.85
CHECK_BELOW = 0.8
MAX_NAME_WORDS = 4
DOB_LOOKBEHIND = 24
MONTHS = {
    name: number
    for number, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}
MONTH_WORD = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
DATE_TEXT = (
    r"(?P<iso>(?P<iy>\d{4})-(?P<im>\d{1,2})-(?P<id>\d{1,2}))"
    r"|(?P<us>(?P<um>\d{1,2})[/-](?P<ud>\d{1,2})[/-](?P<uy>\d{4}|\d{2}))(?![\d/-])"
    rf"|(?P<mdy>(?P<mm>{MONTH_WORD})\s+(?P<md>\d{{1,2}}),?\s+(?P<my>\d{{4}}))"
    rf"|(?P<dmy>(?P<dd>\d{{1,2}})\s+(?P<dm>{MONTH_WORD}),?\s+(?P<dy>\d{{4}}))"
)
DATE = re.compile(rf"(?<![\d/-])(?:{DATE_TEXT})", re.IGNORECASE)
DATE_LABEL = re.compile(
    r"\b(?:date\s+of\s+service|service\s+date|dos|visit\s+date|date\s+of\s+visit|encounter\s+date)\b\s*[:#.-]?\s*",
    re.IGNORECASE,
)
DOB_LABEL = re.compile(r"\b(?:dob|d\.o\.b|date\s+of\s+birth|birth\s*date|born)\b", re.IGNORECASE)
PATIENT_LABEL = re.compile(r"\b(?:patient\s+name|patient)\b\s*[:#-]\s*", re.IGNORECASE)
PLACE_LABEL = re.compile(r"\b(?:place\s+of\s+service|pos)\b\s*[:#-]?\s*", re.IGNORECASE)
NPI_DIGITS = re.compile(r"(?<!\d)(\d{10})(?!\d)")
NAME_TOKEN = re.compile(r"[A-Za-z][A-Za-z'.-]*")
LETTERS = re.compile(r"[a-z]+")
DIGIT = re.compile(r"\d")
PLACE_CODE = re.compile(r"(\d{2})\b")
STOP_WORDS = {
    "dob",
    "date",
    "dos",
    "mrn",
    "provider",
    "physician",
    "rendering",
    "sex",
    "age",
    "gender",
    "visit",
    "place",
    "pos",
    "npi",
    "account",
    "acct",
    "id",
    "seen",
    "service",
    "encounter",
    "male",
    "female",
}


@dataclass(frozen=True)
class ProviderRef:
    id: str
    name: str
    npi: str | None
    place_code: str | None


@dataclass(frozen=True)
class Matched[T]:
    value: T | None
    confidence: float


NOTHING: Matched = Matched(None, 0.0)


@dataclass(frozen=True)
class FileMatch:
    provider: Matched[str]
    service_date: Matched[date]
    place: Matched[str]
    patient: Matched[str]

    @property
    def confidence(self) -> float:
        return min(self.provider.confidence, self.service_date.confidence, self.place.confidence)

    @property
    def needs_check(self) -> bool:
        return self.confidence < CHECK_BELOW


def match_file(
    text: str,
    facts: FilenameFacts,
    providers: Sequence[ProviderRef],
    places: Mapping[str, str],
    *,
    today: date,
) -> FileMatch:
    flat = " ".join(text.split())
    provider = provider_in(flat, providers)
    chosen = next((item for item in providers if item.id == provider.value), None)
    return FileMatch(
        provider=provider,
        service_date=service_date_in(flat, facts.service_date, today=today),
        place=place_in(flat, places, chosen),
        patient=patient_in(flat, facts.patient_name),
    )


def provider_in(text: str, providers: Sequence[ProviderRef]) -> Matched[str]:
    by_npi = {item.npi: item for item in providers if item.npi}
    for digits in NPI_DIGITS.findall(text):
        if is_valid_npi(digits) and digits in by_npi:
            return Matched(by_npi[digits].id, NPI_MATCH)
    words = set(LETTERS.findall(text.lower()))
    named = [(item, parts) for item in providers if (parts := LETTERS.findall(item.name.lower()))]
    full = [item for item, parts in named if {parts[0], parts[-1]} <= words]
    if full:
        return Matched(full[0].id, FULL_NAME if len(full) == 1 else LAST_NAME_ONLY)
    surnames = [parts[-1] for _, parts in named]
    hits = [item for item, parts in named if parts[-1] in words and surnames.count(parts[-1]) == 1]
    return Matched(hits[0].id, LAST_NAME_ONLY) if len(hits) == 1 else NOTHING


def service_date_in(text: str, from_name: date | None, *, today: date) -> Matched[date]:
    labelled = _labelled_date(text, today)
    if labelled is not None and from_name is not None:
        return Matched(labelled, DATES_AGREE if labelled == from_name else DATES_DISAGREE)
    if labelled is not None:
        return Matched(labelled, LABELLED_DATE)
    if from_name is not None and from_name <= today:
        return Matched(from_name, FILE_NAME_DATE)
    found = next((day for day, at in text_dates(text) if day <= today and not _after_birth_label(text, at)), None)
    return Matched(found, UNLABELLED_DATE) if found else NOTHING


def place_in(text: str, places: Mapping[str, str], provider: ProviderRef | None) -> Matched[str]:
    for label in PLACE_LABEL.finditer(text):
        rest = text[label.end() :]
        code = PLACE_CODE.match(rest)
        if code and code.group(1) in places:
            return Matched(code.group(1), LABELLED_PLACE)
        named = next((key for key, name in places.items() if rest.lower().startswith(name.lower())), None)
        if named:
            return Matched(named, LABELLED_PLACE)
    if provider is not None and provider.place_code in places:
        return Matched(provider.place_code, PROVIDER_PLACE)
    return NOTHING


def patient_in(text: str, from_name: str | None) -> Matched[str]:
    for label in PATIENT_LABEL.finditer(text):
        name = _name_after(text[label.end() :])
        if name:
            return Matched(name, LABELLED_PATIENT)
    return Matched(from_name, FILE_NAME_PATIENT) if from_name else NOTHING


def text_dates(text: str) -> list[tuple[date, int]]:
    found: list[tuple[date, int]] = []
    for match in DATE.finditer(text):
        day = _date_of(match)
        if day is not None:
            found.append((day, match.start()))
    return found


def _labelled_date(text: str, today: date) -> date | None:
    for label in DATE_LABEL.finditer(text):
        match = DATE.match(text, label.end())
        day = _date_of(match) if match else None
        if day is not None and day <= today:
            return day
    return None


def _after_birth_label(text: str, at: int) -> bool:
    since_last_number = DIGIT.split(text[max(0, at - DOB_LOOKBEHIND) : at])[-1]
    return DOB_LABEL.search(since_last_number) is not None


def _date_of(match: re.Match[str]) -> date | None:
    parts = match.groupdict()
    if parts["iso"]:
        numbers = (parts["iy"], parts["im"], parts["id"])
    elif parts["us"]:
        year = parts["uy"] if len(parts["uy"]) == 4 else f"20{parts['uy']}"
        numbers = (year, parts["um"], parts["ud"])
    elif parts["mdy"]:
        numbers = (parts["my"], str(MONTHS[parts["mm"].lower().rstrip(".")]), parts["md"])
    else:
        numbers = (parts["dy"], str(MONTHS[parts["dm"].lower().rstrip(".")]), parts["dd"])
    try:
        return date(int(numbers[0]), int(numbers[1]), int(numbers[2]))
    except ValueError:
        return None


def _name_after(rest: str) -> str | None:
    words: list[str] = []
    for token in rest.split()[:MAX_NAME_WORDS]:
        bare = token.rstrip(",.")
        if not NAME_TOKEN.fullmatch(bare) or bare.lower() in STOP_WORDS:
            break
        words.append(token)
    return _formatted_name(words)


def _formatted_name(words: list[str]) -> str | None:
    if not words:
        return None
    cleaned = [word.rstrip(",.") for word in words]
    if words[0].endswith(",") and len(cleaned) > 1:
        cleaned = [*cleaned[1:], cleaned[0]]
    name = " ".join(cleaned)
    return name.title() if name.isupper() or name.islower() else name
