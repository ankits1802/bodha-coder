from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.codes.billing_codes import Code
from app.codes.em import is_em_code

__all__ = [
    "AUDIO_ONLY_MODIFIERS",
    "COMPLEXITY_ADD_ON",
    "COMPLEXITY_MODIFIER",
    "COMPLEXITY_MODIFIER_FROM",
    "COMPLEXITY_WITH_25_EXCEPTIONS",
    "DOWNCODE_LEVELS",
    "NURSING_DISCHARGES",
    "NURSING_INITIAL_VISITS",
    "PLAN_TYPES",
    "TELEHEALTH_FLEXIBILITIES_THROUGH",
    "EarlierVisit",
    "Payer",
    "PayerClaim",
    "PayerFamily",
    "PayerFlag",
    "PlanType",
    "Rule",
    "Severity",
    "initial_nursing_visits",
    "payer_flags",
    "payer_for",
    "repeated_initial_visit",
]

PlanType = Literal["medicare", "medicare_advantage", "medicaid", "commercial"]
PayerFamily = Literal["cigna"]
Severity = Literal["denial", "risk", "reminder"]
Rule = Literal[
    "telehealth_place",
    "audio_only_place",
    "home_telehealth_ended",
    "complexity_with_25",
    "g2211_replaced",
    "level_downcode_risk",
    "audio_only_risk_adjustment",
    "nursing_incident_to",
    "initial_visit_repeated",
]

PLAN_TYPES: tuple[PlanType, ...] = ("medicare", "medicare_advantage", "medicaid", "commercial")
FAMILY_NAMES: tuple[tuple[PayerFamily, str], ...] = (("cigna", "cigna"),)
TELEHEALTH_PLACES = frozenset({"02", "10"})
PATIENT_HOME_TELEHEALTH = "10"
HOSPITAL_OUTPATIENT_PLACES = frozenset({"19", "22"})
NURSING_FACILITY_PLACES = frozenset({"31", "32"})
AUDIO_VIDEO_MODIFIER = "95"
AUDIO_ONLY_MODIFIERS = frozenset({"93", "FQ"})
TELEHEALTH_FLEXIBILITIES_THROUGH = date(2027, 12, 31)
COMPLEXITY_ADD_ON = "G2211"
COMPLEXITY_MODIFIER = "B1"
COMPLEXITY_MODIFIER_FROM = date(2027, 1, 1)
COMPLEXITY_EXCEPTIONS_FROM = date(2025, 1, 1)
SEPARATE_VISIT_MODIFIER = "25"
CR_13705_ATTACHMENT_1 = (
    "71271 76706 76977 77063 77067 77078 77080 77081 77085 90460 90461 90471 90472 90473 90474 96156 96158 "
    "96159 96164 96165 96167 96168 97802 97803 97804 99406 99407 99497 99498 G0101 G0102 G0104 G0105 G0106 "
    "G0108 G0109 G0120 G0121 G0124 G0130 G0136 G0141 G0270 G0271 G0296 G0402 G0403 G0404 G0405 G0438 G0439 "
    "G0442 G0443 G0444 G0445 G0446 G0447 G0473 G0513 G0514 P3001 Q0091"
)
COMPLEXITY_WITH_25_EXCEPTIONS = frozenset(CR_13705_ATTACHMENT_1.split())
DOWNCODE_POLICY_FROM = date(2025, 10, 1)
DOWNCODE_LEVELS = frozenset({"99204", "99205", "99214", "99215", "99244", "99245"})
DOWNCODE_EXEMPT_UNDER_AGE = 1
NON_DISEASE_CHAPTERS = ("R", "Z")
AUDIO_ONLY_RISK_ADJUSTMENT_FROM = date(2026, 1, 1)
NURSING_INITIAL_VISITS = frozenset({"99304", "99305", "99306"})
NURSING_DISCHARGES = frozenset({"99315", "99316"})


@dataclass(frozen=True, slots=True)
class Payer:
    plan: PlanType | None
    family: PayerFamily | None = None


@dataclass(frozen=True, slots=True)
class PayerClaim:
    codes: tuple[Code, ...]
    patient_age: int | None = None
    supervised_nonphysician: bool = False


@dataclass(frozen=True, slots=True)
class PayerFlag:
    rule: Rule
    severity: Severity
    codes: tuple[str, ...] = ()
    earlier: date | None = None

    def as_json(self) -> dict[str, object]:
        found: dict[str, object] = {"rule": self.rule, "severity": self.severity, "codes": list(self.codes)}
        if self.earlier is not None:
            found["earlier"] = self.earlier.isoformat()
        return found


@dataclass(frozen=True, slots=True)
class Visit:
    claim: PayerClaim
    place_code: str
    service_date: date
    procedures: tuple[Code, ...]

    def with_modifier(self, modifiers: frozenset[str]) -> tuple[Code, ...]:
        return tuple(code for code in self.procedures if set(code.modifiers) & modifiers)

    def billed(self, codes: frozenset[str]) -> tuple[Code, ...]:
        return tuple(code for code in self.procedures if code.code in codes)


@dataclass(frozen=True, slots=True)
class EarlierVisit:
    service_date: date
    place_code: str
    code: str
    specialty: str | None = None


RuleCheck = Callable[[Visit], PayerFlag | None]


def payer_for(plan_type: str | None, name: str | None) -> Payer:
    plan = next((known for known in PLAN_TYPES if known == plan_type), None)
    text = (name or "").casefold()
    family = next((family for family, word in FAMILY_NAMES if word in text), None)
    return Payer(plan, family)


def payer_flags(claim: PayerClaim, payer_type: Payer, place_code: str, service_date: date) -> list[PayerFlag]:
    procedures = tuple(code for code in claim.codes if code.type == "CPT")
    visit = Visit(claim, place_code, service_date, procedures)
    applies = [(plans, family, check) for plans, family, check in RULES if payer_type.plan in plans]
    checks = [check for _, family, check in applies if family in (None, payer_type.family)]
    return [flag for check in checks if (flag := check(visit)) is not None]


def initial_nursing_visits(codes: Iterable[Code], place_code: str) -> tuple[Code, ...]:
    if place_code not in NURSING_FACILITY_PLACES:
        return ()
    return tuple(code for code in codes if code.type == "CPT" and code.code in NURSING_INITIAL_VISITS)


def repeated_initial_visit(
    codes: Iterable[Code],
    place_code: str,
    service_date: date,
    history: Iterable[EarlierVisit],
    *,
    specialty: str | None = None,
) -> PayerFlag | None:
    initial = initial_nursing_visits(codes, place_code)
    visits = tuple(history)
    starts = [visit.service_date for visit in visits if _opened_stay(visit, service_date, specialty)]
    if not initial or not starts:
        return None
    earlier = max(starts)
    if any(visit.code in NURSING_DISCHARGES and earlier <= visit.service_date <= service_date for visit in visits):
        return None
    return PayerFlag("initial_visit_repeated", "denial", _labels(initial), earlier)


def _opened_stay(visit: EarlierVisit, before: date, specialty: str | None) -> bool:
    initial = visit.code in NURSING_INITIAL_VISITS and visit.place_code in NURSING_FACILITY_PLACES
    return initial and visit.service_date < before and _same_specialty(visit.specialty, specialty)


def _same_specialty(first: str | None, second: str | None) -> bool:
    if not first or not second:
        return True
    return first.strip().casefold() == second.strip().casefold()


def _telehealth_place(visit: Visit) -> PayerFlag | None:
    allowed = TELEHEALTH_PLACES | HOSPITAL_OUTPATIENT_PLACES
    lines = visit.with_modifier(frozenset({AUDIO_VIDEO_MODIFIER}))
    if not lines or visit.place_code in allowed:
        return None
    return PayerFlag("telehealth_place", "risk", _labels(lines))


def _audio_only_place(visit: Visit) -> PayerFlag | None:
    allowed = {PATIENT_HOME_TELEHEALTH} | HOSPITAL_OUTPATIENT_PLACES
    lines = visit.with_modifier(AUDIO_ONLY_MODIFIERS)
    if not lines or visit.place_code in allowed:
        return None
    return PayerFlag("audio_only_place", "denial", _labels(lines))


def _home_telehealth_ended(visit: Visit) -> PayerFlag | None:
    if visit.place_code != PATIENT_HOME_TELEHEALTH or visit.service_date <= TELEHEALTH_FLEXIBILITIES_THROUGH:
        return None
    return PayerFlag("home_telehealth_ended", "risk", _labels(visit.procedures))


def _complexity_with_25(visit: Visit) -> PayerFlag | None:
    visits = tuple(code for code in visit.with_modifier(frozenset({SEPARATE_VISIT_MODIFIER})) if is_em_code(code.code))
    if visit.service_date < COMPLEXITY_MODIFIER_FROM:
        complexity = visit.billed(frozenset({COMPLEXITY_ADD_ON}))
    else:
        complexity = tuple(code for code in visits if COMPLEXITY_MODIFIER in code.modifiers)
    if not visits or not complexity:
        return None
    excepted = visit.service_date >= COMPLEXITY_EXCEPTIONS_FROM and bool(visit.billed(COMPLEXITY_WITH_25_EXCEPTIONS))
    return None if excepted else PayerFlag("complexity_with_25", "denial", _labels((*visits, *complexity)))


def _g2211_replaced(visit: Visit) -> PayerFlag | None:
    lines = visit.billed(frozenset({COMPLEXITY_ADD_ON}))
    if not lines or visit.service_date < COMPLEXITY_MODIFIER_FROM:
        return None
    return PayerFlag("g2211_replaced", "denial", _labels(lines))


def _level_downcode_risk(visit: Visit) -> PayerFlag | None:
    levels = visit.billed(DOWNCODE_LEVELS)
    age = visit.claim.patient_age
    if not levels or visit.service_date < DOWNCODE_POLICY_FROM or (age is not None and age < DOWNCODE_EXEMPT_UNDER_AGE):
        return None
    diagnoses = [code.code for code in visit.claim.codes if code.type == "ICD-10"]
    if not all(code.startswith(NON_DISEASE_CHAPTERS) for code in diagnoses):
        return None
    return PayerFlag("level_downcode_risk", "risk", _labels(levels))


def _audio_only_risk_adjustment(visit: Visit) -> PayerFlag | None:
    lines = tuple(code for code in visit.with_modifier(AUDIO_ONLY_MODIFIERS) if is_em_code(code.code))
    if not lines or visit.service_date < AUDIO_ONLY_RISK_ADJUSTMENT_FROM:
        return None
    return PayerFlag("audio_only_risk_adjustment", "risk", _labels(lines))


def _nursing_incident_to(visit: Visit) -> PayerFlag | None:
    visits = tuple(code for code in visit.procedures if is_em_code(code.code))
    if not visits or visit.place_code not in NURSING_FACILITY_PLACES or not visit.claim.supervised_nonphysician:
        return None
    return PayerFlag("nursing_incident_to", "reminder", _labels(visits))


def _labels(codes: tuple[Code, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(code.label() for code in codes))


MEDICARE: frozenset[PlanType | None] = frozenset({"medicare"})
RULES: tuple[tuple[frozenset[PlanType | None], PayerFamily | None, RuleCheck], ...] = (
    (MEDICARE, None, _telehealth_place),
    (MEDICARE, None, _audio_only_place),
    (MEDICARE, None, _home_telehealth_ended),
    (MEDICARE, None, _complexity_with_25),
    (MEDICARE, None, _g2211_replaced),
    (frozenset({"commercial"}), "cigna", _level_downcode_risk),
    (frozenset({"medicare_advantage"}), None, _audio_only_risk_adjustment),
    (MEDICARE, None, _nursing_incident_to),
)
