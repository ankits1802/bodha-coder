from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.codes.credentials import LICENSE_STATES, is_taxonomy_code
from app.codes.npi import is_valid_npi
from app.core.errors import Invalid

__all__ = [
    "OPTIONAL_DETAIL_FIELDS",
    "PRACTICE_DETAIL_FIELDS",
    "PRACTICE_DETAILS",
    "BillingProfile",
    "billing_profile",
    "missing_from_profile",
    "validated_practice_details",
]

PRACTICE_DETAILS = "practice_details"
PRACTICE_DETAIL_FIELDS = (
    "legal_name",
    "tax_id",
    "group_npi",
    "taxonomy_code",
    "address",
    "address_line_2",
    "city",
    "state",
    "zip",
    "phone",
    "billing_contact",
)
OPTIONAL_DETAIL_FIELDS = ("taxonomy_code", "address_line_2")
TEXT_LIMITS = {"legal_name": 60, "address": 55, "address_line_2": 55, "city": 30, "billing_contact": 60}
NON_DIGITS = re.compile(r"\D")
ZIP_TEXT = re.compile(r"^\d{5}(-?\d{4})?$")
EIN_DIGITS, PHONE_DIGITS, ZIP_PLUS_FOUR = 9, 10, 9
SEPARATORS = re.compile(r"[*:^~]")


@dataclass(frozen=True)
class BillingProfile:
    legal_name: str | None
    tax_id: str | None
    group_npi: str | None
    taxonomy: str | None
    street: str | None
    street_2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    phone: str | None
    contact: str | None


def validated_practice_details(values: Mapping[str, str]) -> dict[str, str]:
    clean = {field: str(values.get(field, "")).strip() for field in PRACTICE_DETAIL_FIELDS}
    for field, value in clean.items():
        problem = _problem(field, value) if value else None
        if problem:
            raise Invalid(problem)
    clean["state"], clean["taxonomy_code"] = clean["state"].upper(), clean["taxonomy_code"].upper()
    return clean


def billing_profile(setup: Mapping[str, Any]) -> BillingProfile:
    stored = {field: str(value).strip() for field, value in (setup.get(PRACTICE_DETAILS) or {}).items()}

    def kept(field: str) -> str | None:
        value = stored.get(field, "")
        return value if value and _problem(field, value) is None else None

    def digits(field: str, length: int) -> str | None:
        value = kept(field)
        found = NON_DIGITS.sub("", value) if value else ""
        return found if len(found) == length else None

    return BillingProfile(
        legal_name=kept("legal_name"),
        tax_id=digits("tax_id", EIN_DIGITS),
        group_npi=kept("group_npi"),
        taxonomy=(kept("taxonomy_code") or "").upper() or None,
        street=kept("address"),
        street_2=kept("address_line_2"),
        city=kept("city"),
        state=(kept("state") or "").upper() or None,
        zip_code=digits("zip", ZIP_PLUS_FOUR),
        phone=digits("phone", PHONE_DIGITS),
        contact=kept("billing_contact"),
    )


def missing_from_profile(profile: BillingProfile) -> list[str]:
    needed = {
        "practice.legal_name": profile.legal_name,
        "practice.tax_id": profile.tax_id,
        "practice.address": profile.street,
        "practice.city": profile.city,
        "practice.state": profile.state,
        "practice.zip": profile.zip_code,
        "practice.phone": profile.phone,
        "practice.billing_contact": profile.contact,
    }
    return [key for key, value in needed.items() if not value]


def _problem(field: str, value: str) -> str | None:
    label = field.replace("_", " ")
    limit = TEXT_LIMITS.get(field)
    if limit is not None and len(value) > limit:
        return f"{label} is longer than {limit} characters"
    if SEPARATORS.search(value):
        return f"{label} cannot hold *, :, ^ or ~"
    return _shape_problem(field, value)


def _shape_problem(field: str, value: str) -> str | None:
    digits = NON_DIGITS.sub("", value)
    if field == "tax_id" and (len(digits) != EIN_DIGITS or not re.fullmatch(r"\d{2}-?\d{7}", value)):
        return "the tax ID must be the nine-digit EIN, like 12-3456789"
    if field == "group_npi" and not is_valid_npi(value):
        return f"{value} is not a valid group NPI"
    if field == "taxonomy_code" and not is_taxonomy_code(value.upper()):
        return f"{value} is not a taxonomy code (10 characters ending in X)"
    if field == "state" and value.upper() not in LICENSE_STATES:
        return f"{value} is not a US state or territory"
    if field == "zip" and ZIP_TEXT.fullmatch(value) is None:
        return "the ZIP code must be five digits or ZIP+4"
    if field == "phone" and len(digits) != PHONE_DIGITS:
        return "the phone number must have ten digits"
    return None
