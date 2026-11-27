from __future__ import annotations

__all__ = ["ADJUSTMENT_GROUPS", "CONTRACTUAL", "DOWNCODE_REASONS", "PATIENT_RESPONSIBILITY", "describe_adjustment"]

CONTRACTUAL = "CO"
PATIENT_RESPONSIBILITY = "PR"
ADJUSTMENT_GROUPS = {
    "CO": "Contractual obligation",
    "CR": "Correction and reversal",
    "OA": "Other adjustment",
    "PI": "Payer initiated reduction",
    "PR": "Patient responsibility",
}
DOWNCODE_REASONS = frozenset({"150", "152"})
REASONS = {
    "1": "Deductible Amount",
    "2": "Coinsurance Amount",
    "3": "Co-payment Amount",
    "45": "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement.",
    "50": "These are non-covered services because this is not deemed a 'medical necessity' by the payer.",
    "97": (
        "The benefit for this service is included in the payment/allowance for another service/procedure "
        "that has already been adjudicated."
    ),
    "150": "Payer deems the information submitted does not support this level of service.",
    "152": "Payer deems the information submitted does not support this length of service.",
}


def describe_adjustment(group: str, reason: str) -> str:
    label = f"{group}-{reason}"
    meaning = REASONS.get(reason)
    return f"{label} {meaning}" if meaning else label
