from __future__ import annotations

NPI_LENGTH = 10
HEALTHCARE_PREFIX = "80840"


def is_valid_npi(npi: str) -> bool:
    if len(npi) != NPI_LENGTH or not npi.isdigit():
        return False
    digits = [int(digit) for digit in HEALTHCARE_PREFIX + npi[:-1]]
    total = 0
    for position, digit in enumerate(reversed(digits)):
        doubled = digit * 2 if position % 2 == 0 else digit
        total += doubled - 9 if doubled > 9 else doubled
    return (10 - total % 10) % 10 == int(npi[-1])
