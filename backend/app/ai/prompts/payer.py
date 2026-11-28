from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.codes.payer_rules import FAMILY_NAMES, PLAN_TYPES, Payer

__all__ = ["OTHER_PLAN", "PAYER_STEP", "payer_facts", "payer_from_record", "payer_record", "reads_alike"]

OTHER_PLAN = "other"
NOT_MEDICARE = "not_medicare"
GUIDED_PLANS = frozenset({"medicare", "medicare_advantage"})

PAYER_STEP = """
# STEP 6: THE PAYER

The ENCOUNTER CONTEXT's payer is the claim's payer. When payer is null the payer is not known yet: apply the steps
above as written. When payer is given, the rules below for its planType and family take the place of the general
wording above. They change which code or modifier you name, never what the note must document.

planType "medicare" (traditional Medicare, Part B):
- Prolonged service: G2212, never 99417: 89 minutes or more with 99205, 69 minutes or more with 99215, and one more
  unit for each further full 15 minutes.
- Telehealth: Medicare pays telehealth by place of service 02 or 10, not by an in-person place with modifier 95.
  Suggest 95 only when the place of service is 02, 10, 19 or 22. Audio-only (93) is for a patient at home only:
  place of service 10, 19 or 22.
- Visit complexity: for a date of service through 2026-12-31, put G2211 in add_on_codes with an office or home
  E/M (99202-99215, 99341-99350) when the note documents that the practitioner is the continuing focal point for
  all of the patient's needed services, or gives ongoing care for a single serious or complex condition. Never
  with an E/M that carries modifier 25, unless billedCodes also has an annual wellness visit, the IPPE, a vaccine
  administration or another Part B preventive service. For a date of service in 2027 or later G2211 is not paid:
  never suggest it.

planType "medicare_advantage":
- Prolonged service: G2212 as for Medicare, never 99417, and say in its reason that the plan's own prolonged
  service policy decides.
- Audio-only (93 or FQ): for a date of service in 2026 or later, diagnoses from an audio-only visit do not count
  for risk adjustment; when the note documents an audio-only visit, say so in the reason of modifier 93.

planType "commercial", "medicaid" or "other":
- Prolonged service: 99417, never G2212.
- G2211 and G2212 are Medicare codes: never suggest them.

family "cigna" (a commercial plan):
- From 2025-10-01 Cigna may lower 99204-99205, 99214-99215 and 99244-99245 by one level when the claim's diagnoses
  do not support the level. Select the level on the documentation as always, and name in justification the
  documented problems that carry it.
"""


def payer_record(payer: Payer | None) -> dict[str, str | None] | None:
    if payer is None:
        return None
    return {"plan_type": payer.plan or OTHER_PLAN, "family": payer.family}


def payer_facts(payer: Payer | None) -> dict[str, str | None] | None:
    record = payer_record(payer)
    return None if record is None else {"planType": record["plan_type"], "family": record["family"]}


def payer_from_record(record: Mapping[str, Any] | None) -> Payer | None:
    if not record:
        return None
    plan = next((known for known in PLAN_TYPES if known == record.get("plan_type")), None)
    family = next((known for known, _ in FAMILY_NAMES if known == record.get("family")), None)
    return Payer(plan, family)


def reads_alike(first: Payer | None, second: Payer | None) -> bool:
    return _guidance(first) == _guidance(second)


def _guidance(payer: Payer | None) -> tuple[str, str | None] | None:
    if payer is None:
        return None
    return (payer.plan if payer.plan in GUIDED_PLANS else NOT_MEDICARE, payer.family)
