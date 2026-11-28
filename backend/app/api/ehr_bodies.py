from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.api.bodies import Body
from app.codes.clinical_notes import NOTE_TYPES, NoteType
from app.models import EHR_CLIENT_ID_LENGTH, EHR_KEY_ALGORITHMS, EHR_URL_LENGTH

__all__ = ["DEFAULT_ALGORITHM", "EhrConnectionBody", "EhrKeyBody"]

DEFAULT_ALGORITHM = "RS384"
SCOPE_LENGTH = 200
MAX_SCOPES = 12

ScopeText = Annotated[str, StringConstraints(min_length=1, max_length=SCOPE_LENGTH)]


class EhrConnectionBody(Body):
    base_url: str = Field(min_length=8, max_length=EHR_URL_LENGTH)
    client_id: str = Field(min_length=1, max_length=EHR_CLIENT_ID_LENGTH)
    scopes: list[ScopeText] = Field(min_length=1, max_length=MAX_SCOPES)
    note_types: list[NoteType] = Field(min_length=1, max_length=len(NOTE_TYPES))
    start_date: date


class EhrKeyBody(Body):
    algorithm: Literal[EHR_KEY_ALGORITHMS] = DEFAULT_ALGORITHM
