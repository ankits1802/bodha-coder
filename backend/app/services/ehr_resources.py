from __future__ import annotations

import re
from collections.abc import Collection, Iterator, Mapping
from datetime import date, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.codes.clinical_notes import (
    ACT_CODE_SYSTEM,
    AMBULATORY_CLASS,
    AMBULATORY_PLACE,
    CLASS_PLACES,
    LOINC_SYSTEM,
    NPI_SYSTEM,
    POS_SYSTEM,
)
from app.codes.npi import is_valid_npi

__all__ = [
    "Attachment",
    "DocumentReference",
    "Encounter",
    "Practitioner",
    "chosen_attachment",
    "documents_in",
    "fhir_day",
    "fhir_id",
    "is_final",
    "is_wanted",
    "npi_of",
    "place_for",
    "practitioner_references",
    "read_encounter",
    "read_practitioner",
    "reference_id",
    "service_day",
]

PDF = "application/pdf"
HTML = "text/html"
PLAIN = "text/plain"
READABLE_TYPES = (PDF, HTML, PLAIN)
FHIR_ID = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")
REFERENCE = re.compile(
    r"^(?:https://[^\s#?]+/)?(?P<type>[A-Za-z]+)/(?P<id>[A-Za-z0-9\-.]{1,64})(?:/_history/[^/\s]+)?$"
)
DAY_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}")
PERFORMER_TYPES = ("PPRF", "ATND", "SPRF", "PART")


class Shape(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Coding(Shape):
    system: str | None = None
    code: str | None = None


class Concept(Shape):
    coding: list[Coding] = []


class Reference(Shape):
    reference: str | None = None


class Period(Shape):
    start: str | None = None


class Meta(Shape):
    versionId: str | None = None
    lastUpdated: str | None = None


class Attachment(Shape):
    contentType: str | None = None
    url: str | None = None
    data: str | None = None
    size: int | None = None
    hash: str | None = None

    @property
    def media_type(self) -> str:
        return (self.contentType or "").split(";")[0].strip().lower()


class Content(Shape):
    attachment: Attachment


class Context(Shape):
    encounter: list[Reference] = []
    period: Period | None = None

    @field_validator("encounter", mode="before")
    @classmethod
    def one_or_many(cls, value: Any) -> Any:
        return [value] if isinstance(value, dict) else value


class DocumentReference(Shape):
    resourceType: Literal["DocumentReference"]
    id: str
    meta: Meta = Meta()
    status: str | None = None
    docStatus: str | None = None
    type: Concept | None = None
    date: str | None = None
    author: list[Reference] = []
    context: Context | None = None
    content: list[Content] = []

    @property
    def version(self) -> str:
        return (self.meta.versionId or self.meta.lastUpdated or "1")[:64]


class Participant(Shape):
    individual: Reference | None = None
    type: list[Concept] = []


class Encounter(Shape):
    resourceType: Literal["Encounter"]
    id: str
    period: Period | None = None
    kind: Coding | list[Concept] | None = Field(default=None, alias="class")
    type: list[Concept] = []
    serviceType: Concept | list[Concept] | None = None
    participant: list[Participant] = []


class Identifier(Shape):
    system: str | None = None
    value: str | None = None


class Practitioner(Shape):
    resourceType: Literal["Practitioner"]
    id: str
    identifier: list[Identifier] = []


def documents_in(bundle: Mapping[str, Any]) -> Iterator[DocumentReference | None]:
    entries = bundle.get("entry")
    for entry in entries if isinstance(entries, list) else []:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict) or resource.get("resourceType") != "DocumentReference":
            continue
        try:
            yield DocumentReference.model_validate(resource)
        except ValidationError:
            yield None


def read_encounter(resource: Mapping[str, Any]) -> Encounter | None:
    try:
        return Encounter.model_validate(resource)
    except ValidationError:
        return None


def read_practitioner(resource: Mapping[str, Any]) -> Practitioner | None:
    try:
        return Practitioner.model_validate(resource)
    except ValidationError:
        return None


def fhir_id(value: str | None) -> str | None:
    return value if value and FHIR_ID.fullmatch(value) else None


def reference_id(reference: Reference | None, resource_type: str) -> str | None:
    found = REFERENCE.fullmatch((reference.reference or "") if reference else "")
    return found.group("id") if found and found.group("type") == resource_type else None


def is_wanted(document: DocumentReference, codes: Collection[str]) -> bool:
    if document.status != "current" or document.type is None:
        return False
    return any(coding.system == LOINC_SYSTEM and coding.code in codes for coding in document.type.coding)


def is_final(document: DocumentReference) -> bool:
    return document.docStatus == "final"


def chosen_attachment(document: DocumentReference) -> Attachment | None:
    readable = [item.attachment for item in document.content if item.attachment.media_type in READABLE_TYPES]
    for media_type in READABLE_TYPES:
        found = next((item for item in readable if item.media_type == media_type), None)
        if found is not None and (found.url or found.data):
            return found
    return None


def service_day(encounter: Encounter | None, document: DocumentReference, zone: ZoneInfo) -> date | None:
    starts = [encounter.period.start if encounter and encounter.period else None]
    starts.append(document.context.period.start if document.context and document.context.period else None)
    return next((day for start in starts if start and (day := fhir_day(start, zone)) is not None), None)


def practitioner_references(document: DocumentReference, encounter: Encounter | None) -> list[str]:
    found = [ref for item in document.author if (ref := _practitioner(item))]
    participants = encounter.participant if encounter else []
    ordered = sorted(participants, key=_participant_rank)
    found += [ref for item in ordered if (ref := _practitioner(item.individual))]
    return list(dict.fromkeys(found))


def npi_of(practitioner: Practitioner) -> str | None:
    for identifier in practitioner.identifier:
        value = (identifier.value or "").strip()
        if identifier.system == NPI_SYSTEM and is_valid_npi(value):
            return value
    return None


def place_for(encounter: Encounter | None, provider_place: str | None, allowed: Collection[str]) -> str | None:
    candidates = [*_coded_places(encounter), _class_place(encounter), provider_place]
    if _class_code(encounter) == AMBULATORY_CLASS:
        candidates.append(AMBULATORY_PLACE)
    return next((code for code in candidates if code and code in allowed), None)


def fhir_day(text: str, zone: ZoneInfo) -> date | None:
    if DAY_TEXT.match(text) is None:
        return None
    if len(text) == 10:
        return _plain_day(text)
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone(zone).date() if moment.tzinfo else moment.date()


def _practitioner(reference: Reference | None) -> str | None:
    found = REFERENCE.fullmatch((reference.reference or "") if reference else "")
    return found.group(0) if found and found.group("type") == "Practitioner" else None


def _participant_rank(participant: Participant) -> int:
    codes = [coding.code for concept in participant.type for coding in concept.coding]
    ranks = [PERFORMER_TYPES.index(code) for code in codes if code in PERFORMER_TYPES]
    return min(ranks, default=len(PERFORMER_TYPES))


def _coded_places(encounter: Encounter | None) -> list[str]:
    if encounter is None:
        return []
    service = encounter.serviceType
    concepts = [*encounter.type, *(service if isinstance(service, list) else [service] if service else [])]
    return [
        coding.code for concept in concepts for coding in concept.coding if coding.system == POS_SYSTEM and coding.code
    ]


def _class_code(encounter: Encounter | None) -> str | None:
    kind = encounter.kind if encounter else None
    if isinstance(kind, Coding):
        return kind.code if kind.system in (None, ACT_CODE_SYSTEM) else None
    codings = [coding for concept in kind or [] for coding in concept.coding if coding.system == ACT_CODE_SYSTEM]
    return codings[0].code if codings else None


def _class_place(encounter: Encounter | None) -> str | None:
    return CLASS_PLACES.get(_class_code(encounter) or "")


def _plain_day(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
