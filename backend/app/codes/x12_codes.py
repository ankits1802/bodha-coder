from __future__ import annotations

__all__ = [
    "ACCEPTED_CATEGORIES",
    "ACK_ACCEPTED",
    "ACK_REJECTED",
    "CLAIM_FILING_CODES",
    "ELEMENT_ERRORS",
    "GROUP_ERRORS",
    "REJECTED_CATEGORIES",
    "SEGMENT_ERRORS",
    "STATUS_CATEGORIES",
    "TRANSACTION_ERRORS",
    "default_filing_code",
]

CLAIM_FILING_CODES = (
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "AM",
    "BL",
    "CH",
    "CI",
    "DS",
    "FI",
    "HM",
    "LM",
    "MA",
    "MB",
    "MC",
    "OF",
    "TV",
    "VA",
    "WC",
    "ZZ",
)
FILING_BY_PLAN_TYPE = {"commercial": "CI", "medicare": "MB", "medicare_advantage": "16", "medicaid": "MC"}

ACK_ACCEPTED = ("A", "E")
ACK_REJECTED = ("M", "R", "W", "X")

SEGMENT_ERRORS = {
    "1": "unrecognized segment",
    "2": "unexpected segment",
    "3": "required segment missing",
    "4": "loop occurs over maximum times",
    "5": "segment exceeds maximum use",
    "6": "segment not in defined transaction set",
    "7": "segment not in proper sequence",
    "8": "segment has data element errors",
    "I4": "segment not used in this implementation is present",
    "I6": "implementation dependent segment missing",
    "I7": "implementation loop occurs under minimum times",
    "I8": "implementation segment below minimum use",
    "I9": "implementation dependent segment not used is present",
}
ELEMENT_ERRORS = {
    "1": "required data element missing",
    "2": "conditional required data element missing",
    "3": "too many data elements",
    "4": "data element too short",
    "5": "data element too long",
    "6": "invalid character in data element",
    "7": "invalid code value",
    "8": "invalid date",
    "9": "invalid time",
    "10": "exclusion condition violated",
    "12": "too many repetitions",
    "13": "too many components",
    "I6": "code value not used in this implementation",
    "I9": "implementation dependent data element missing",
    "I10": "data element not used in this implementation is present",
    "I11": "implementation too few repetitions",
    "I12": "implementation pattern match failure",
    "I13": "implementation dependent data element not used is present",
}
TRANSACTION_ERRORS = {
    "1": "transaction set not supported",
    "2": "transaction set trailer missing",
    "3": "transaction set control numbers in header and trailer do not match",
    "4": "number of included segments does not match actual count",
    "5": "one or more segments in error",
    "6": "missing or invalid transaction set identifier",
    "7": "missing or invalid transaction set control number",
    "18": "transaction set not in functional group",
    "19": "invalid transaction set implementation convention reference",
    "23": "transaction set control number not unique within the functional group",
    "I5": "implementation one or more segments in error",
    "I6": "implementation convention not supported",
}
GROUP_ERRORS = {
    "1": "functional group not supported",
    "2": "functional group version not supported",
    "3": "functional group trailer missing",
    "4": "group control numbers in header and trailer do not agree",
    "5": "number of included transaction sets does not match actual count",
    "6": "group control number violates syntax",
    "19": "functional group control number not unique within interchange",
}
STATUS_CATEGORIES = {
    "A0": "forwarded to another entity",
    "A1": "received",
    "A2": "accepted into adjudication",
    "A3": "returned as unprocessable",
    "A4": "not found",
    "A5": "split claim",
    "A6": "rejected for missing information",
    "A7": "rejected for invalid information",
    "A8": "rejected for a related field in error",
    "E0": "error in the submitted data",
    "E1": "payer system unavailable",
    "E2": "payer not responding; send again later",
    "E3": "correction required in related fields",
    "E4": "trading partner requirement not met; correction required",
}
ACCEPTED_CATEGORIES = frozenset({"A0", "A1", "A2", "A5"})
REJECTED_CATEGORIES = frozenset({"A3", "A4", "A6", "A7", "A8", "E0", "E3", "E4"})


def default_filing_code(plan_type: str | None) -> str | None:
    return FILING_BY_PLAN_TYPE.get(plan_type or "")
