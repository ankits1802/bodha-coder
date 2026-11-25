from __future__ import annotations

import re
from typing import Any

from .cms_mips_2026 import CMS_MIPS_2026, NOT_DOCUMENTABLE, PERFORMANCE_YEAR

VERIFIED_MIPS_MEASURES: dict[str, tuple[str, str]] = {
    "001": (
        "Diabetes: Glycemic Status Assessment Greater Than 9%",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_001_MIPSCQM.pdf",
    ),
    "048": (
        "Urinary Incontinence: Assessment of Presence or Absence of Urinary Incontinence in Women Aged 65 Years and Older",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_048_MIPSCQM.pdf",
    ),
    "117": (
        "Diabetes: Eye Exam",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_117_MIPSCQM.pdf",
    ),
    "128": (
        "Preventive Care and Screening: Body Mass Index (BMI) Screening and Follow-Up Plan",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_128_MIPSCQM.pdf",
    ),
    "130": (
        "Documentation of Current Medications in the Medical Record",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_130_MIPSCQM.pdf",
    ),
    "134": (
        "Preventive Care and Screening: Screening for Depression and Follow-Up Plan",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_134_MIPSCQM.pdf",
    ),
    "226": (
        "Preventive Care and Screening: Tobacco Use: Screening and Cessation Intervention",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_226_MIPSCQM.pdf",
    ),
    "236": (
        "Controlling High Blood Pressure",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_236_MIPSCQM.pdf",
    ),
    "318": (
        "Falls: Screening for Future Fall Risk",
        "https://ecqi.healthit.gov/ecqm/ec/2026/cms0139v14",
    ),
    "326": (
        "Atrial Fibrillation and Atrial Flutter: Chronic Anticoagulation Therapy",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_326_MIPSCQM.pdf",
    ),
    "431": (
        "Preventive Care and Screening: Unhealthy Alcohol Use: Screening & Brief Counseling",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_431_MIPSCQM.pdf",
    ),
    "493": (
        "Adult Immunization Status",
        "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_493_MIPSCQM.pdf",
    ),
}


MIPS_MEASURES_WITHOUT_A_CODE_LIST: dict[str, str] = {
    "318": (
        "eCQM only in 2026 (CMS139v14, https://ecqi.healthit.gov/ecqm/ec/2026/cms0139v14): "
        "reported from a certified EHR's value sets. CMS publishes no MIPS CQM or Medicare Part B "
        "Claims specification for it in 2026, so there is no quality-data code to report and the "
        "card shows none."
    ),
}


NO_NURSING_FACILITY_VISIT_NOTE = (
    "CMS 2026: a nursing-facility visit is not a qualifying encounter for this measure's "
    "denominator, so a nursing-facility visit does not by itself place the patient in it; the "
    "patient counts only through a qualifying visit of another kind in the performance period."
)
MEASURES_WITHOUT_A_NURSING_FACILITY_VISIT = frozenset({"001", "048", "117", "226", "236", "431"})

ADDED_MEASURE_NURSING_FACILITY_NOTE = (
    "CMS 2026: a nursing-facility visit is not a qualifying encounter for this measure's "
    "denominator, so a nursing-facility visit does not by itself place the patient in it."
)


def catalog_entries() -> list[dict[str, Any]]:
    return [
        {
            "id": measure_id,
            "title": title,
            "specUrl": spec_url,
            "hasReportingCodes": measure_id not in MIPS_MEASURES_WITHOUT_A_CODE_LIST,
            "nursingFacilityNote": (
                NO_NURSING_FACILITY_VISIT_NOTE
                if measure_id in MEASURES_WITHOUT_A_NURSING_FACILITY_VISIT
                else None
            ),
        }
        for measure_id, (title, spec_url) in VERIFIED_MIPS_MEASURES.items()
    ]


CMS_MIPS_INDEX: dict[str, dict[str, Any]] = CMS_MIPS_2026

NOT_DOCUMENTABLE_MEASURES: dict[str, str] = NOT_DOCUMENTABLE

ADDABLE_MEASURE_IDS: frozenset[str] = frozenset(
    measure_id
    for measure_id in CMS_MIPS_INDEX
    if measure_id not in VERIFIED_MIPS_MEASURES and measure_id not in NOT_DOCUMENTABLE_MEASURES
)

SPECIFIED_ADDED_MEASURE_IDS: frozenset[str] = frozenset({"047", "126", "155", "238", "317"})
assert SPECIFIED_ADDED_MEASURE_IDS <= ADDABLE_MEASURE_IDS, "a specified measure must stay addable by code"

MIPS_MEASURE_BUILT_IN = "MIPS_MEASURE_BUILT_IN"
MIPS_MEASURE_NOT_DOCUMENTABLE = "MIPS_MEASURE_NOT_DOCUMENTABLE"
MIPS_MEASURE_UNKNOWN = "MIPS_MEASURE_UNKNOWN"

_ECHO_MAX = 12

_MEASURE_INPUT = re.compile(r"^\s*(?:mips\s*)?(?:quality\s*id\s*)?#?\s*(\d{1,3})\s*$", re.IGNORECASE)


class MipsMeasureRejected(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def normalise_measure_input(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _MEASURE_INPUT.match(value)
    return match.group(1).zfill(3) if match else None


def is_added_measure(measure_id: object) -> bool:
    return isinstance(measure_id, str) and measure_id in ADDABLE_MEASURE_IDS


def addable_measure(measure_id: object) -> dict[str, Any] | None:
    if not is_added_measure(measure_id):
        return None
    entry = CMS_MIPS_INDEX[measure_id]
    return {**entry, "submissionMethods": tuple(entry["submissionMethods"])}


def org_added_entry(measure_id: object) -> dict[str, Any] | None:
    entry = addable_measure(measure_id)
    if entry is None:
        return None
    return {
        "id": measure_id,
        "title": entry["title"],
        "description": entry["description"],
        "specUrl": entry["specUrl"],
        "nursingFacilityNote": (
            ADDED_MEASURE_NURSING_FACILITY_NOTE if entry["nursingFacilityVisitInDenominator"] is False else None
        ),
        "reportedFromCertifiedEhrOnly": entry["submissionMethods"] == ("electronicHealthRecord",),
        "hasReportingCodes": measure_id in SPECIFIED_ADDED_MEASURE_IDS,
    }


def list_order(measure_ids: Any) -> list[str]:
    chosen = {item for item in measure_ids if isinstance(item, str)}
    built_in = [measure_id for measure_id in VERIFIED_MIPS_MEASURES if measure_id in chosen]
    return built_in + sorted(chosen & ADDABLE_MEASURE_IDS)


def _not_documentable(measure_id: str) -> MipsMeasureRejected:
    return MipsMeasureRejected(
        f"#{measure_id} is calculated by CMS from claims or surveys, so a note cannot document it.",
        MIPS_MEASURE_NOT_DOCUMENTABLE,
    )


def unknown_measure(raw: object, *, exact: bool = False) -> MipsMeasureRejected:
    text = raw if exact and isinstance(raw, str) else (raw.strip() if isinstance(raw, str) else "")
    if text and len(text) <= _ECHO_MAX and text.isprintable():
        shown = f'"{text}"' if exact else text
        message = f"{shown} is not a {PERFORMANCE_YEAR} CMS quality measure code."
    else:
        message = f"That is not a {PERFORMANCE_YEAR} CMS quality measure code."
    return MipsMeasureRejected(message, MIPS_MEASURE_UNKNOWN)


def rejection_for_saved_id(item: str) -> MipsMeasureRejected:
    padded = normalise_measure_input(item)
    if padded is not None and padded in NOT_DOCUMENTABLE_MEASURES:
        return _not_documentable(padded)
    rejection = unknown_measure(item, exact=True)
    if padded is not None and padded != item and (padded in VERIFIED_MIPS_MEASURES or padded in ADDABLE_MEASURE_IDS):
        rejection = MipsMeasureRejected(f'{rejection.message} Use "{padded}".', rejection.code)
    return rejection


def lookup_cms_measure(raw: object) -> dict[str, Any]:
    measure_id = normalise_measure_input(raw)
    if measure_id is None or measure_id not in CMS_MIPS_INDEX:
        raise unknown_measure(raw)
    if measure_id in VERIFIED_MIPS_MEASURES:
        raise MipsMeasureRejected(
            f"#{measure_id} is already in the list above — tick it there.", MIPS_MEASURE_BUILT_IN
        )
    if measure_id in NOT_DOCUMENTABLE_MEASURES:
        raise _not_documentable(measure_id)
    entry = org_added_entry(measure_id)
    assert entry is not None
    return entry
