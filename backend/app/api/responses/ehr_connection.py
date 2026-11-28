from typing import Literal

from app.codes.clinical_notes import NoteType
from app.models import DOCUMENT_OUTCOMES, DOCUMENT_REASONS, EHR_KEY_ALGORITHMS, PULL_REASONS
from app.services.ehr_checks import CHECK_STEPS
from app.services.ehr_views import AUTH_METHOD, CONNECTION_STATUSES, GRANT_TYPE, RUN_STATES

from .base import Omittable
from .view import View

__all__ = [
    "EhrCheckStepView",
    "EhrCheckView",
    "EhrConnectionSettingsView",
    "EhrConnectionView",
    "EhrDocumentPage",
    "EhrDocumentView",
    "EhrPullRunPage",
    "EhrPullRunView",
    "EhrRegistrationView",
    "JwksView",
    "PublicJwk",
]


class EhrRegistrationView(View):
    jwks_url: str
    key_id: str
    algorithm: Literal[EHR_KEY_ALGORITHMS]
    key_created_at: str
    grant_type: Literal[GRANT_TYPE]
    auth_method: Literal[AUTH_METHOD]


class EhrConnectionSettingsView(View):
    base_url: str
    token_endpoint: str
    client_id: str
    scopes: list[str]
    note_types: list[NoteType]
    start_date: str
    paused: bool
    saved_at: str


class EhrPullRunView(View):
    id: str
    started_at: str
    finished_at: str | None
    outcome: Literal[RUN_STATES]
    reason: Literal[PULL_REASONS] | None
    pages: int
    accepted: int
    duplicates: int
    refused: int
    skipped: int


class EhrConnectionView(View):
    available: bool
    status: Literal[CONNECTION_STATUSES]
    registration: EhrRegistrationView | None
    connection: EhrConnectionSettingsView | None
    default_scopes: list[str]
    last_run: EhrPullRunView | None


class EhrCheckStepView(View):
    step: Literal[CHECK_STEPS]
    passed: bool
    detail: str


class EhrCheckView(View):
    passed: bool
    tested_at: str
    steps: list[EhrCheckStepView]


class EhrPullRunPage(View):
    items: list[EhrPullRunView]
    total: int
    offset: int
    page_size: int


class EhrDocumentView(View):
    id: str
    fetched_at: str
    document_id: str
    outcome: Literal[DOCUMENT_OUTCOMES]
    reason: Literal[DOCUMENT_REASONS] | None
    note_id: str | None


class EhrDocumentPage(View):
    items: list[EhrDocumentView]
    total: int
    offset: int
    page_size: int


class PublicJwk(View):
    kty: Literal["RSA", "EC"]
    kid: str
    alg: Literal[EHR_KEY_ALGORITHMS]
    use: Literal["sig"]
    key_ops: list[Literal["verify"]]
    n: Omittable[str] = None
    e: Omittable[str] = None
    crv: Omittable[str] = None
    x: Omittable[str] = None
    y: Omittable[str] = None


class JwksView(View):
    keys: list[PublicJwk]
