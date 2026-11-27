from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.mips_catalog import ADDABLE_MEASURE_IDS, VERIFIED_MIPS_MEASURES, addable_measure
from app.codes.mips_scope import validate_measure_ids
from app.codes.npi import is_valid_npi
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.core.roles import PRACTICE_ROLES
from app.models import DEFAULT_CHECKS, MipsList, PlaceOfService, Practice, Provider
from app.services.audit_log import record_activity
from app.services.payers import has_active_payer, payer_list
from app.services.plan_limits import ensure_provider_room
from app.services.provider_channels import CHANNELS, CONTACT_FIELDS, EMAIL, TEXT, usable_channel
from app.services.provider_details import DETAIL_FIELDS, validated_details

SETUP_SECTIONS: dict[str, tuple[str, ...]] = {
    "practice_details": ("legal_name", "tax_id", "group_npi", "address", "phone", "billing_contact"),
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
IDLE_MINUTES_CHOICES = (5, 10, 15, 30)
ACCESS_LOG_YEARS = range(6, 11)
NO_CONTACT = "questions need an email or phone to be sent to"


def section_complete(values: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(str(values.get(field, "")).strip() for field in fields)


async def setup_overview(db: AsyncSession, practice: Practice) -> dict[str, Any]:
    providers = (
        await db.scalars(select(Provider).where(Provider.practice_id == practice.id, Provider.active.is_(True)))
    ).all()
    sections = {key: _section_view(practice, key, fields) for key, fields in SETUP_SECTIONS.items()}
    sections["providers"] = {"fields": [], "values": {}, "complete": bool(providers) and all(p.npi for p in providers)}
    return {
        "sections": sections,
        "complete": sum(1 for item in sections.values() if item["complete"]),
        "total": len(sections),
        "checks": practice_checks(practice),
        "missing_npi": sum(1 for p in providers if not p.npi),
        "payers": payer_list(practice),
    }


def _section_view(practice: Practice, key: str, fields: tuple[str, ...]) -> dict[str, Any]:
    stored = practice.setup.get(key, {})
    complete = section_complete(stored, fields) and (key != "payers" or has_active_payer(practice))
    return {"fields": list(fields), "values": {field: stored.get(field, "") for field in fields}, "complete": complete}


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
    practice.setup = {**practice.setup, key: {**kept, **{field: values.get(field, "").strip() for field in fields}}}
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
        raise Invalid("keep the access log for 6 to 10 years")
    practice = actor.practice
    if practice is None:
        raise NotFound("practice not found")
    practice.mfa_roles, practice.idle_minutes = sorted(set(mfa_roles)), idle_minutes
    practice.access_log_years = access_log_years or practice.access_log_years
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


async def mips_overview(db: AsyncSession, practice_id: str) -> dict[str, Any]:
    stored = await db.scalar(select(MipsList.measure_ids).where(MipsList.practice_id == practice_id))
    addable = [
        {"id": mid, "title": (addable_measure(mid) or {}).get("title", "")} for mid in sorted(ADDABLE_MEASURE_IDS)
    ]
    return {
        "standard": [{"id": mid, "title": title} for mid, (title, _spec) in VERIFIED_MIPS_MEASURES.items()],
        "addable": addable,
        "measure_ids": stored or [],
        "uses_standard": not stored,
    }


async def save_mips(db: AsyncSession, actor: Actor, *, measure_ids: list[str], expected: list[str]) -> list[str]:
    row = await db.scalar(select(MipsList).where(MipsList.practice_id == actor.practice_id).with_for_update())
    if (row.measure_ids if row else []) != expected:
        raise Conflict("someone else changed this list; reload and try again")
    try:
        chosen = validate_measure_ids(measure_ids)
    except ValueError as error:
        raise Invalid(str(error)) from error
    if not chosen and row is not None:
        await db.delete(row)
    elif row is None and chosen:
        db.add(MipsList(practice_id=actor.practice_id, measure_ids=chosen, updated_by=actor.user.id))
    elif row is not None:
        row.measure_ids, row.updated_by = chosen, actor.user.id
    record_activity(
        db, actor, "MIPS list changed", practice_id=actor.practice_id, detail=", ".join(chosen) or "standard list"
    )
    await db.commit()
    return chosen
