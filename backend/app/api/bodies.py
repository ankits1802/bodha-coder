from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.codes.billing_codes import MAX_POINTERS
from app.models import ACCESS_DETAIL_LENGTH, BILLING_INTERVALS, BILLING_PROVIDERS, TOUR_OUTCOMES, TOUR_VERSION_LIMIT
from app.services.plans import CHECKOUT_PLANS


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


class PreviewBody(Body):
    file_names: list[str] = Field(max_length=500)


class DecisionsBody(Body):
    choices: dict[str, Literal["accept", "keep", "ask", "add", "skip"]] = Field(min_length=1)


class BilledBody(Body):
    codes: str = Field(max_length=500)


class PointerLineBody(Body):
    code: str = Field(min_length=5, max_length=5)
    pointers: list[Annotated[str, Field(min_length=3, max_length=8)]] = Field(max_length=MAX_POINTERS)


class PointersBody(Body):
    lines: list[PointerLineBody] = Field(min_length=1, max_length=50)


class FlagBody(Body):
    reason: str = Field(min_length=3, max_length=2000)


class ComplianceBody(Body):
    decision: Literal["confirm", "return", "keep"]
    reason: str | None = Field(default=None, max_length=ACCESS_DETAIL_LENGTH)


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


class DeleteNotesBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=500)


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
    access_log_years: int | None = Field(default=None, ge=6, le=10)


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


class RespondBody(Body):
    answers: list[AnswerBody] = Field(min_length=1, max_length=10)
    confirmed: bool


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


class DeletePracticeBody(Body):
    confirm_name: str = Field(min_length=1, max_length=200)


class RenewBody(Body):
    until: date | None


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


class CheckoutBody(Body):
    plan: Literal[CHECKOUT_PLANS]
    interval: Literal[BILLING_INTERVALS]
    provider: Literal[BILLING_PROVIDERS]
