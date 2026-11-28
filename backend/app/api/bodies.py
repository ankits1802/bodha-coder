from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.codes.billing_codes import MAX_POINTERS
from app.codes.x12_codes import CLAIM_FILING_CODES
from app.models import (
    ACCESS_DETAIL_LENGTH,
    ACCESS_LOG_MAX_YEARS,
    ACCESS_LOG_MIN_YEARS,
    BILLING_INTERVALS,
    BILLING_PROVIDERS,
    COMMENT_LENGTH,
    LANES,
    OVERRIDE_NOTE_LENGTH,
    OVERRIDE_REASONS,
    QUEUE_VIEW_NAME_LENGTH,
    RETURN_REASONS,
    SIGNATURE_SOURCES,
    SIGNER_NAME_LENGTH,
    TOUR_OUTCOMES,
    TOUR_VERSION_LIMIT,
)
from app.models.tables import LANE_REASONS
from app.services.note_voids import REASON_LENGTH
from app.services.plans import CHECKOUT_PLANS
from app.services.signature_images import MAX_IMAGE_DATA_CHARS
from app.services.worklists import ASSIGNED_PATTERN, DUE_SORT, QUEUE_SORTS


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginBody(Body):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class MfaBody(Body):
    mfa_token: str
    code: str = Field(pattern=r"^\d{6}$")


class MfaStartBody(Body):
    mfa_token: str


class PasswordBody(Body):
    token: str
    password: str = Field(min_length=10, max_length=200)


class ForgotBody(Body):
    email: EmailStr


class RecoveryBody(Body):
    mfa_token: str
    recovery_code: str = Field(min_length=16, max_length=40)


class MfaCodeBody(Body):
    code: str = Field(pattern=r"^\d{6}$")


class PreferencesBody(Body):
    notify_digest: bool


class TourBody(Body):
    version: int = Field(ge=1, le=TOUR_VERSION_LIMIT)
    outcome: Literal[TOUR_OUTCOMES]


class OverrideBody(Body):
    reason: Literal[OVERRIDE_REASONS]
    note: str | None = Field(default=None, max_length=OVERRIDE_NOTE_LENGTH)


class DecisionsBody(Body):
    choices: dict[str, Literal["accept", "keep", "ask", "add", "skip"]] = Field(min_length=1)
    reasons: dict[str, OverrideBody] = Field(default_factory=dict)


class BilledBody(Body):
    codes: str = Field(max_length=500)
    reason: OverrideBody


class PointerLineBody(Body):
    code: str = Field(min_length=5, max_length=5)
    pointers: list[Annotated[str, Field(min_length=3, max_length=8)]] = Field(max_length=MAX_POINTERS)


class PointersBody(Body):
    lines: list[PointerLineBody] = Field(min_length=1, max_length=50)
    reason: OverrideBody


class FlagBody(Body):
    reason: str = Field(min_length=3, max_length=2000)


class ReturnReasonBody(Body):
    reason: Literal[RETURN_REASONS]
    note: str | None = Field(default=None, max_length=OVERRIDE_NOTE_LENGTH)


class ComplianceBody(Body):
    decision: Literal["confirm", "return", "keep"]
    reason: str | None = Field(default=None, max_length=ACCESS_DETAIL_LENGTH)
    override: OverrideBody | None = None
    return_reason: ReturnReasonBody | None = None


class QuestionBody(Body):
    key: str
    text: str = Field(max_length=1000)


class AskBody(Body):
    questions: list[QuestionBody] = Field(min_length=1, max_length=10)
    channel: Literal["email", "sms"]
    hold: bool = True


class BulkApproveBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=200)


class BulkReopenBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=200)


class VoidNotesBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=REASON_LENGTH)


class RestoreNoteBody(Body):
    reason: str = Field(min_length=3, max_length=REASON_LENGTH)


class AssignBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=500)
    user_id: str | None = Field(max_length=36)


class PayerChoiceBody(Body):
    payer: str | None = Field(default=None, max_length=64)


class VisitTypeBody(Body):
    visit_type: str = Field(min_length=1, max_length=40)


class RetryBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=500)


class ExportBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=500)
    again: bool = False


class SectionBody(Body):
    values: dict[str, str]


class ChecksBody(Body):
    checks: dict[str, bool]


class SecurityBody(Body):
    mfa_roles: list[str]
    idle_minutes: int
    access_log_years: int | None = Field(default=None, ge=ACCESS_LOG_MIN_YEARS, le=ACCESS_LOG_MAX_YEARS)


class ProviderDetailsBody(Body):
    taxonomy_code: str | None = Field(default=None, max_length=10)
    license_number: str | None = Field(default=None, max_length=40)
    license_state: str | None = Field(default=None, max_length=2)
    dea_number: str | None = Field(default=None, max_length=9)
    bills_under: Literal["individual", "group"] | None = None
    group_npi: str | None = Field(default=None, max_length=10)
    supervising_physician: str | None = Field(default=None, max_length=120)
    signature_on_file: bool = False


class ProviderBody(Body):
    name: str = Field(max_length=120)
    credential: str = Field(max_length=16)
    specialty: str | None = Field(default=None, max_length=80)
    npi: str | None = Field(default=None, max_length=10)
    place_code: str | None = Field(default=None, max_length=2)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    channel: Literal["email", "sms"] | None = None
    active: bool = True
    details: ProviderDetailsBody | None = None


class PayerBody(Body):
    name: str = Field(min_length=1, max_length=120)
    payer_id: str | None = Field(default=None, max_length=15)
    plan_type: Literal["commercial", "medicare", "medicare_advantage", "medicaid", "other"]
    claim_filing: Literal[CLAIM_FILING_CODES] | None = None
    active: bool = True


class ImportBody(Body):
    csv: str = Field(max_length=500_000)


class MipsBody(Body):
    measure_ids: list[str]
    expected_measure_ids: list[str]


class InviteBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: str


class MemberBody(Body):
    role: str | None = None
    blocked: bool | None = None


class HqInviteBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr


class HqMemberBody(Body):
    blocked: bool


class CodeRequestBody(Body):
    token: str


class CodeVerifyBody(Body):
    token: str
    code: str = Field(pattern=r"^\d{6}$")


class AnswerBody(Body):
    key: str
    choice: str = Field(max_length=200)
    comment: str | None = Field(default=None, max_length=2000)


class SignatureDraftBody(Body):
    source: Literal[SIGNATURE_SOURCES]
    typed_name: str = Field(min_length=1, max_length=SIGNER_NAME_LENGTH)
    image: str = Field(min_length=1, max_length=MAX_IMAGE_DATA_CHARS)


class ProviderSigningBody(Body):
    signature_id: str | None = Field(default=None, max_length=36)
    remember_signature: bool = False


class RespondBody(ProviderSigningBody):
    answers: list[AnswerBody] = Field(min_length=1, max_length=10)
    confirmed: bool
    attestation: str | None = Field(default=None, max_length=300)


class LevelChangeBody(ProviderSigningBody):
    answer: Literal["confirm", "disagree"]
    comment: str | None = Field(default=None, max_length=COMMENT_LENGTH)
    confirmed: bool
    attestation: str | None = Field(default=None, max_length=300)


class CommentBody(Body):
    finding_key: str | None = Field(default=None, max_length=80)
    body: str = Field(min_length=1, max_length=COMMENT_LENGTH)
    mentions: list[str] = Field(default_factory=list, max_length=20)


class ReviewSettingsBody(Body):
    confirm_level_changes: bool
    hold_until_confirmed: bool


class SwitchBody(Body):
    request_id: str = Field(min_length=1, max_length=36)


class PracticeBody(Body):
    name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=1, max_length=120)
    admin_email: EmailStr
    plan: str
    seats: int = Field(ge=1, le=10_000)
    time_zone: str = Field(default="America/Chicago", max_length=64)


class PracticeUpdateBody(Body):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status: str | None = None
    plan: str | None = None
    seats: int | None = Field(default=None, ge=1, le=10_000)
    renews_on: date | None = None
    time_zone: str | None = Field(default=None, max_length=64)


class ConfirmPracticeBody(Body):
    confirm_name: str = Field(min_length=1, max_length=200)


class AccessLogExportBody(Body):
    start: date | None = None
    end: date | None = None
    user_id: str | None = Field(default=None, max_length=36)
    action: str | None = Field(default=None, max_length=40)
    note_id: str | None = Field(default=None, max_length=36)
    patient: str | None = Field(default=None, max_length=200)
    birth_date: date | None = None


class RenewBody(Body):
    until: date | None
    plan: str | None = Field(default=None, min_length=1, max_length=16)


class PlaceBody(Body):
    name: str | None = Field(default=None, max_length=80)
    active: bool


class DemoBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    organization: str = Field(min_length=1, max_length=200)
    message: str | None = Field(default=None, max_length=2000)


class IdentitySignupBody(Body):
    name: str = Field(min_length=1, max_length=120)
    practice_name: str = Field(min_length=2, max_length=200)
    time_zone: str = Field(min_length=1, max_length=64)
    agreed: Literal[True]


class SignupBody(IdentitySignupBody):
    email: EmailStr


class NewPracticeBody(Body):
    practice_name: str = Field(min_length=2, max_length=200)
    time_zone: str = Field(min_length=1, max_length=64)
    agreed: Literal[True]


class SwitchPracticeBody(Body):
    practice_id: str = Field(min_length=1, max_length=36)


class HqAdminBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    reason: str = Field(min_length=3, max_length=200)


class CheckoutBody(Body):
    plan: Literal[CHECKOUT_PLANS]
    interval: Literal[BILLING_INTERVALS]
    provider: Literal[BILLING_PROVIDERS]


class InboxReadBody(Body):
    ids: list[str] = Field(default_factory=list, max_length=500)
    all: bool = False


class QueueViewFiltersBody(Body):
    lane: Literal[LANES] | None = None
    reason: Literal[LANE_REASONS] | None = None
    assigned: str | None = Field(default=None, pattern=ASSIGNED_PATTERN)
    provider_id: str | None = Field(default=None, max_length=36)
    overdue: bool = False
    sort: Literal[QUEUE_SORTS] = DUE_SORT


class QueueViewBody(Body):
    name: str = Field(min_length=1, max_length=QUEUE_VIEW_NAME_LENGTH)
    filters: QueueViewFiltersBody
