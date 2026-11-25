from __future__ import annotations

from typing import Literal

Setting = Literal["office", "nursing_facility", "inpatient", "emergency", "home", "telehealth"]

SETTING_BY_PLACE: dict[str, Setting] = {
    "11": "office",
    "22": "office",
    "12": "home",
    "13": "home",
    "02": "telehealth",
    "10": "telehealth",
    "21": "inpatient",
    "23": "emergency",
    "31": "nursing_facility",
    "32": "nursing_facility",
}


class UnknownPlaceOfService(LookupError):
    pass


def setting_for(place_code: str) -> Setting:
    if place_code not in SETTING_BY_PLACE:
        raise UnknownPlaceOfService(f"place of service {place_code} has no care setting")
    return SETTING_BY_PLACE[place_code]
