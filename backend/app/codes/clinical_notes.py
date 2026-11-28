from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

__all__ = [
    "ACT_CODE_SYSTEM",
    "AMBULATORY_CLASS",
    "AMBULATORY_PLACE",
    "CLASS_PLACES",
    "LOINC_SYSTEM",
    "NOTE_TYPES",
    "NOTE_TYPE_CODES",
    "NPI_SYSTEM",
    "POS_SYSTEM",
    "NoteType",
    "loinc_codes_for",
]

LOINC_SYSTEM = "http://loinc.org"
NPI_SYSTEM = "http://hl7.org/fhir/sid/us-npi"
POS_SYSTEM = "https://www.cms.gov/Medicare/Coding/place-of-service-codes/Place_of_Service_Code_Set"
ACT_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"

NoteType = Literal["progress", "consult", "history_physical", "nursing_facility"]
NOTE_TYPES: tuple[NoteType, ...] = ("progress", "consult", "history_physical", "nursing_facility")
NOTE_TYPE_CODES: dict[NoteType, tuple[str, ...]] = {
    "progress": ("11506-3",),
    "consult": ("11488-4",),
    "history_physical": ("34117-2",),
    "nursing_facility": ("34113-1", "34119-8", "34096-8", "67856-5", "34116-4", "68672-5"),
}

AMBULATORY_CLASS = "AMB"
AMBULATORY_PLACE = "11"
CLASS_PLACES = {"EMER": "23", "IMP": "21", "ACUTE": "21", "OBSENC": "22", "HH": "12"}


def loinc_codes_for(note_types: Iterable[NoteType]) -> frozenset[str]:
    return frozenset(code for note_type in note_types for code in NOTE_TYPE_CODES[note_type])
