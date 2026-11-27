from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.codes.credentials import LICENSE_STATES, is_taxonomy_code, is_valid_dea
from app.codes.npi import is_valid_npi
from app.core.errors import Invalid

__all__ = ["DETAIL_FIELDS", "details_view", "validated_details"]

TEXT_FIELDS = (
    "taxonomy_code",
    "license_number",
    "license_state",
    "dea_number",
    "bills_under",
    "group_npi",
    "supervising_physician",
)
DETAIL_FIELDS = (*TEXT_FIELDS, "signature_on_file")
UPPERCASE_FIELDS = ("taxonomy_code", "license_number", "license_state", "dea_number")
BILLS_UNDER = ("individual", "group")
TEXT_LIMITS = {"license_number": 40, "supervising_physician": 120}
YES = ("yes", "y", "true", "1")
NO = ("no", "n", "false", "0", "")


def details_view(stored: Mapping[str, Any]) -> dict[str, Any]:
    return {field: stored.get(field) for field in TEXT_FIELDS} | {
        "signature_on_file": bool(stored.get("signature_on_file"))
    }


def validated_details(values: Mapping[str, Any]) -> dict[str, Any]:
    unknown = set(values) - set(DETAIL_FIELDS)
    if unknown:
        raise Invalid(f"unknown provider details: {', '.join(sorted(unknown))}")
    clean = {field: _text(values.get(field)) for field in TEXT_FIELDS}
    for field in UPPERCASE_FIELDS:
        clean[field] = clean[field].upper() if clean[field] else None
    clean["bills_under"] = clean["bills_under"].lower() if clean["bills_under"] else None
    _check_lengths(clean)
    _check_identifiers(clean)
    return clean | {"signature_on_file": _yes_no(values.get("signature_on_file"))}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _check_lengths(clean: Mapping[str, str | None]) -> None:
    for field, limit in TEXT_LIMITS.items():
        if len(clean[field] or "") > limit:
            raise Invalid(f"{field.replace('_', ' ')} is longer than {limit} characters")


def _check_identifiers(clean: Mapping[str, str | None]) -> None:
    if clean["taxonomy_code"] and not is_taxonomy_code(clean["taxonomy_code"]):
        raise Invalid(f"{clean['taxonomy_code']} is not a taxonomy code (10 characters ending in X)")
    if bool(clean["license_number"]) != bool(clean["license_state"]):
        raise Invalid("give the state license number together with its state")
    if clean["license_state"] and clean["license_state"] not in LICENSE_STATES:
        raise Invalid(f"{clean['license_state']} is not a US state or territory")
    if clean["dea_number"] and not is_valid_dea(clean["dea_number"]):
        raise Invalid(f"{clean['dea_number']} is not a valid DEA number")
    if clean["group_npi"] and not is_valid_npi(clean["group_npi"]):
        raise Invalid(f"{clean['group_npi']} is not a valid group NPI")
    if clean["bills_under"] and clean["bills_under"] not in BILLS_UNDER:
        raise Invalid(f"bills under must be one of: {', '.join(BILLS_UNDER)}")


def _yes_no(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = "" if value is None else str(value).strip().lower()
    if text in YES:
        return True
    if text in NO:
        return False
    raise Invalid(f"signature on file must be yes or no, not {value}")
