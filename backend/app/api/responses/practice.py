from typing import Literal

from app.api.responses.auth import Checks
from app.api.responses.base import Channel, PlanType, PracticeRole, View
from app.services.practice_setup import ACCESS_LOG_YEARS, IDLE_MINUTES_CHOICES
from app.services.provider_details import BILLS_UNDER

__all__ = [
    "AccessLogEntry",
    "AccessLogPage",
    "ImportedProviders",
    "IntakeView",
    "MipsChoice",
    "MipsMeasure",
    "MipsOverview",
    "Payer",
    "PayerOption",
    "Place",
    "PracticeSetup",
    "Provider",
    "ProviderDetails",
    "SecuritySettings",
    "SetupSection",
    "SetupSections",
]


class SetupSection(View):
    fields: list[str]
    values: dict[str, str]
    complete: bool


class SetupSections(View):
    practice_details: SetupSection
    payers: SetupSection
    payments: SetupSection
    coding_rules: SetupSection
    charge_capture: SetupSection
    documentation_rules: SetupSection
    compliance: SetupSection
    reports: SetupSection
    contacts: SetupSection
    patient_registration: SetupSection
    software: SetupSection
    providers: SetupSection


class SecuritySettings(View):
    mfa_roles: list[PracticeRole]
    idle_minutes: Literal[IDLE_MINUTES_CHOICES]
    access_log_years: Literal[tuple(ACCESS_LOG_YEARS)]


class Payer(View):
    id: str
    name: str
    payer_id: str | None
    plan_type: PlanType
    active: bool


class PracticeSetup(View):
    sections: SetupSections
    complete: int
    total: int
    checks: Checks
    missing_npi: int
    payers: list[Payer]
    security: SecuritySettings


class PayerOption(View):
    id: str
    name: str
    plan_type: PlanType | None


class ProviderDetails(View):
    taxonomy_code: str | None
    license_number: str | None
    license_state: str | None
    dea_number: str | None
    bills_under: Literal[BILLS_UNDER] | None
    group_npi: str | None
    supervising_physician: str | None
    signature_on_file: bool


class Provider(View):
    id: str
    name: str
    credential: str
    specialty: str | None
    npi: str | None
    place_code: str | None
    email: str | None
    phone: str | None
    channel: Channel
    active: bool
    details: ProviderDetails


class ImportedProviders(View):
    imported: int


class Place(View):
    code: str
    name: str


class MipsMeasure(View):
    id: str
    title: str


class MipsOverview(View):
    standard: list[MipsMeasure]
    addable: list[MipsMeasure]
    measure_ids: list[str]
    uses_standard: bool


class MipsChoice(View):
    measure_ids: list[str]


class AccessLogEntry(View):
    at: str
    actor: str
    actor_kind: Literal["user", "provider", "system"]
    action: str
    note_id: str | None
    detail: str | None
    ip: str | None
    user_agent: str | None


class AccessLogPage(View):
    items: list[AccessLogEntry]
    total: int
    offset: int
    page_size: int


class IntakeView(View):
    enabled: bool
    prefix: str
    provider_by_folder: dict[str, str]
    place_code: str | None
    visit_type: str
    watched_prefix: str
