from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class PreviewBody(Body):
    file_names: list[str] = Field(max_length=500)


class DecisionsBody(Body):
    choices: dict[str, Literal["accept", "keep", "ask", "add", "skip"]] = Field(min_length=1)


class BilledBody(Body):
    codes: str = Field(max_length=500)


class FlagBody(Body):
    reason: str = Field(min_length=3, max_length=2000)


class ComplianceBody(Body):
    decision: Literal["confirm", "return", "keep"]
    reason: str | None = Field(default=None, max_length=2000)


class QuestionBody(Body):
    key: str
    text: str = Field(max_length=1000)


class AskBody(Body):
    questions: list[QuestionBody] = Field(min_length=1, max_length=10)
    channel: Literal["email", "sms"]
    hold: bool = True


class BulkApproveBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=200)


class DeleteNotesBody(Body):
    note_ids: list[str] = Field(min_length=1, max_length=500)


class VisitTypeBody(Body):
    visit_type: str = Field(min_length=1, max_length=40)


class RetryBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=500)


class ExportBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=500)


class SectionBody(Body):
    values: dict[str, str]


class ChecksBody(Body):
    checks: dict[str, bool]


class SecurityBody(Body):
    mfa_roles: list[str]
    idle_minutes: int
    private_messages: bool


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


class PracticeBody(Body):
    name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=1, max_length=120)
    admin_email: EmailStr
    plan: str
    seats: int = Field(ge=1, le=10_000)
    time_zone: str = Field(default="America/Chicago", max_length=64)


class PracticeUpdateBody(Body):
    status: str | None = None
    plan: str | None = None
    seats: int | None = Field(default=None, ge=1, le=10_000)
    renews_on: date | None = None
    time_zone: str | None = Field(default=None, max_length=64)


class PlaceBody(Body):
    name: str | None = Field(default=None, max_length=80)
    active: bool


class DemoBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    organization: str = Field(min_length=1, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
