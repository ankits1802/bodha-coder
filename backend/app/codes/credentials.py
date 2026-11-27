from __future__ import annotations

import re

__all__ = ["LICENSE_STATES", "is_taxonomy_code", "is_valid_dea"]

TAXONOMY_CODE = re.compile(r"^[0-9A-Z]{9}X$")
DEA_NUMBER = re.compile(r"^[A-Z][A-Z9][0-9]{7}$")
STATE_CODES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR "
    "PA RI SC SD TN TX UT VT VA WA WV WI WY PR VI GU AS MP"
)
LICENSE_STATES = frozenset(STATE_CODES.split())


def is_taxonomy_code(code: str) -> bool:
    return TAXONOMY_CODE.fullmatch(code) is not None


def is_valid_dea(number: str) -> bool:
    if DEA_NUMBER.fullmatch(number) is None:
        return False
    digits = [int(digit) for digit in number[2:]]
    total = digits[0] + digits[2] + digits[4] + 2 * (digits[1] + digits[3] + digits[5])
    return total % 10 == digits[6]
