from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.npi import is_valid_npi
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.core.roles import PRACTICE_ROLES
from app.models import (
    ACCESS_LOG_MAX_YEARS,
    ACCESS_LOG_MIN_YEARS,
    DEFAULT_CHECKS,
    PlaceOfService,
    Practice,
    Provider,
)
from app.services.audit_log import record_activity
from app.services.billing_profile import (
    OPTIONAL_DETAIL_FIELDS,
    PRACTICE_DETAIL_FIELDS,
    PRACTICE_DETAILS,
    validated_practice_details,
)
from app.services.first_run import CHECKS_REVIEWED, SECURITY_REVIEWED, first_run_view, mark_first_run
from app.services.payers import has_active_payer, payer_list, require_active_payer
from app.services.plan_limits import ensure_provider_room
from app.services.provider_channels import CHANNELS, CONTACT_FIELDS, EMAIL, TEXT, usable_channel
from app.services.provider_details import DETAIL_FIELDS, validated_details

SETUP_SECTIONS: dict[str, tuple[str, ...]] = {
    PRACTICE_DETAILS: PRACTICE_DETAIL_FIELDS,
    "payers": ("clearinghouse", "eft_era_status"),
    "payments": ("fee_schedule", "payment_posting", "write_off_rules"),
    "coding_rules": ("common_codes", "modifier_rules", "coding_preferences"),
    "charge_capture": ("charge_route", "turnaround", "reconciliation"),
    "documentation_rules": ("signature_policy", "time_documentation", "medical_necessity"),
    "compliance": ("baa_on_file", "addendum_policy", "audit_response", "compliance_contact"),
    "reports": ("kpis", "report_recipients"),
    "contacts": ("front_desk", "clinical_lead", "escalation_contact"),
    "patient_registration": ("eligibility_checks", "consent_forms"),
    "software": ("ehr", "practice_management"),
}
PROVIDER_FIELDS = ("name", "credential", "specialty", "npi", "place_code", "email", "phone", "channel")
CREDENTIALS = ("MD", "DO", "NP", "PA", "CNS", "CNM")
IDLE_MINUTES_CHOICES = (15, 30, 60, 240, 480, 1440, 10_080)
ACCESS_LOG_YEARS = range(ACCESS_LOG_MIN_YEARS, ACCESS_LOG_MAX_YEARS + 1)
NO_CONTACT = "questions need an email or phone to be sent to"
OPTIONAL_FIELDS = {PRACTICE_DETAILS: OPTIONAL_DETAIL_FIELDS}


def section_complete(values: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(str(values.get(field, "")).strip() for field in fields)


async def setup_overview(db: AsyncSession, practice: Practice) -> dict[str, Any]:
    providers = (
        await db.scalars(select(Provider).where(Provider.practice_id == practice.id, Provider.active.is_(True)))
    ).all()
    sections = {key: _section_view(practice, key, fields) for key, fields in SETUP_SECTIONS.items()}
    sections["providers"] = {
        "fields": [],
        "optional": [],
        "values": {},
        "complete": bool(providers) and all(p.npi for p in providers),
    }
    return {
        "sections": sections,
        "complete": sum(1 for item in sections.values() if item["complete"]),
        "total": len(sections),
        "checks": practice_checks(practice),
        "missing_npi": sum(1 for p in providers if not p.npi),
        "payers": payer_list(practice),
        "first_run": first_run_view(practice),
    }


def _section_view(practice: Practice, key: str, fields: tuple[str, ...]) -> dict[str, Any]:
    stored = practice.setup.get(key, {})
    required = tuple(field for field in fields if field not in OPTIONAL_FIELDS.get(key, ()))
    complete = section_complete(stored, required) and (key != "payers" or has_active_payer(practice))
    return {
        "fields": list(fields),
        "optional": list(OPTIONAL_FIELDS.get(key, ())),
        "values": {field: stored.get(field, "") for field in fields},
        "complete": complete,
    }


async def save_section(db: AsyncSession, actor: Actor, key: str, values: dict[str, str]) -> None:
    fields = SETUP_SECTIONS.get(key)
    if fields is None:
        raise NotFound("setup section not found")
    unknown = set(values) - set(fields)
    if unknown:
        raise Invalid(f"unknown fields: {', '.join(sorted(unknown))}")
    practice = actor.practice
    if practice is None:
        raise NotFound("practice not found")
    kept = practice.setup.get(key, {})
    cleaned = validated_practice_details(values) if key == PRACTICE_DETAILS else values
    practice.setup = {**practice.setup, key: {**kept, **{field: cleaned.get(field, "").strip() for field in fields}}}
    record_activity(db, actor, "setup saved", practice_id=practice.id, detail=key)
    await db.commit()


def practice_checks(practice: Practice) -> dict[str, bool]:
    return {**DEFAULT_CHECKS, **practice.checks}


async def save_checks(db: AsyncSession, actor: Actor, checks: dict[str, bool]) -> None:
    if set(checks) != set(DEFAULT_CHECKS):
        raise Invalid(f"checks must be exactly: {', '.join(DEFAULT_CHECKS)}")
    if checks["hcc"] and not checks["icd"]:
        raise Invalid("risk adjustment needs the diagnosis check")
    practice = actor.practice
    if practice is None:
        raise NotFound("practice not found")
    practice.checks = dict(checks)
    mark_first_run(practice, CHECKS_REVIEWED)
    record_activity(
        db, actor, "checks changed", practice_id=practice.id, detail=", ".join(k for k, on in checks.items() if on)
    )
    await db.commit()


async def save_security(
    db: AsyncSession, actor: Actor, *, mfa_roles: list[str], idle_minutes: int, access_log_years: int | None
) -> None:
    if not set(mfa_roles) <= set(PRACTICE_ROLES) or idle_minutes not in IDLE_MINUTES_CHOICES:
        raise Invalid("choose roles and an inactivity limit from the list")
    if access_log_years is not None and access_log_years not in ACCESS_LOG_YEARS:
        raise Invalid(f"keep the access log for {ACCESS_LOG_MIN_YEARS} to {ACCESS_LOG_MAX_YEARS} years")
    practice = actor.practice
    if practice is None:
        raise NotFound("practice not found")
    practice.mfa_roles, practice.idle_minutes = sorted(set(mfa_roles)), idle_minutes
    practice.access_log_years = access_log_years or practice.access_log_years
    mark_first_run(practice, SECURITY_REVIEWED)
    record_activity(
        db,
        actor,
        "security changed",
        practice_id=practice.id,
        detail=(
            f"two-step: {', '.join(practice.mfa_roles) or 'none'}; sign-out {idle_minutes} min; "
            f"access log kept {practice.access_log_years} years"
        ),
    )
    await db.commit()


def review_settings(practice: Practice) -> dict[str, bool]:
    return {
        "confirm_level_changes": practice.confirm_level_changes,
        "hold_until_confirmed": practice.confirm_level_changes and practice.hold_until_confirmed,
    }


async def save_review_settings(db: AsyncSession, actor: Actor, *, confirm: bool, hold: bool) -> dict[str, bool]:
    practice = actor.own_practice
    practice.confirm_level_changes, practice.hold_until_confirmed = confirm, confirm and hold
    saved = review_settings(practice)
    detail = (
        f"confirm level changes {'on' if confirm else 'off'}; hold {'on' if saved['hold_until_confirmed'] else 'off'}"
    )
    record_activity(db, actor, "review settings changed", practice_id=practice.id, detail=detail)
    await db.commit()
    return saved


async def validated_provider(db: AsyncSession, values: dict[str, Any]) -> dict[str, Any]:
    clean = {field: (str(values.get(field) or "").strip() or None) for field in PROVIDER_FIELDS}
    if not clean["name"] or clean["credential"] not in CREDENTIALS:
        raise Invalid(f"each provider needs a name and a credential ({', '.join(CREDENTIALS)})")
    if clean["npi"] and not is_valid_npi(clean["npi"]):
        raise Invalid(f"{clean['npi']} is not a valid NPI")
    if clean["place_code"] and await db.get(PlaceOfService, clean["place_code"]) is None:
        raise Invalid(f"unknown place of service {clean['place_code']}")
    preferred = clean["channel"] or (TEXT if clean["phone"] and not clean["email"] else EMAIL)
    if preferred not in CHANNELS:
        raise Invalid(NO_CONTACT)
    clean["channel"] = usable_channel(preferred, name=clean["name"], email=clean["email"])
    if not clean[CONTACT_FIELDS[clean["channel"]]]:
        raise Invalid(NO_CONTACT)
    return clean


async def save_provider(db: AsyncSession, actor: Actor, values: dict[str, Any], *, provider_id: str | None) -> Provider:
    clean = {**await validated_provider(db, values), "active": bool(values.get("active", True))}
    clean["payer"] = _usual_payer(actor.own_practice, values.get("payer"))
    if values.get("details") is not None:
        clean["details"] = validated_details(values["details"])
    provider = await _provider_to_save(db, actor, provider_id)
    if clean["active"] and not provider.active:
        await ensure_provider_room(db, actor.own_practice, 1)
    for field, value in clean.items():
        setattr(provider, field, value)
    db.add(provider)
    record_activity(db, actor, "provider saved", practice_id=actor.practice_id, detail=clean["name"] or "")
    await db.commit()
    return provider


def _usual_payer(practice: Practice, chosen: Any) -> str | None:
    payer_key = str(chosen or "").strip() or None
    if payer_key is not None:
        require_active_payer(practice, payer_key)
    return payer_key


async def _provider_to_save(db: AsyncSession, actor: Actor, provider_id: str | None) -> Provider:
    if provider_id is None:
        return Provider(practice_id=actor.practice_id, details={}, active=False)
    provider = await db.get(Provider, provider_id)
    if provider is None or provider.practice_id != actor.practice_id:
        raise NotFound("provider not found")
    return provider


async def import_providers(db: AsyncSession, actor: Actor, csv_text: str) -> int:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    cleaned = []
    for number, row in enumerate(rows, start=2):
        values = {key.strip().lower(): value for key, value in row.items() if key}
        try:
            details = validated_details({field: values[field] for field in DETAIL_FIELDS if field in values})
            cleaned.append({**await validated_provider(db, values), "details": details})
        except Invalid as error:
            raise Invalid(f"row {number}: {error.message}") from error
    await ensure_provider_room(db, actor.own_practice, len(cleaned))
    for values in cleaned:
        db.add(Provider(practice_id=actor.practice_id, **values))
    record_activity(db, actor, "providers imported", practice_id=actor.practice_id, detail=f"{len(cleaned)} providers")
    await db.commit()
    return len(cleaned)
