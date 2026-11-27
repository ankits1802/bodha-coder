from datetime import date

import pytest

from app.codes.billing_codes import parse_code_list
from app.codes.payer_rules import Payer, PayerClaim, payer_flags, payer_for

MEDICARE = Payer("medicare")
ADVANTAGE = Payer("medicare_advantage")
CIGNA = Payer("commercial", "cigna")
NOVEMBER_2026 = date(2026, 11, 25)
JANUARY_2027 = date(2027, 1, 5)


def _flags(text: str, payer: Payer, place: str = "11", day: date = NOVEMBER_2026, **facts) -> list[tuple]:
    claim = PayerClaim(parse_code_list(text).codes, **facts)
    return [(flag.rule, flag.severity, flag.codes) for flag in payer_flags(claim, payer, place, day)]


@pytest.mark.parametrize(
    ("plan_type", "name", "payer"),
    [
        ("medicare", "Medicare Part B", Payer("medicare")),
        ("commercial", "Cigna Open Access Plus", Payer("commercial", "cigna")),
        ("commercial", "Aetna Choice", Payer("commercial")),
        ("medicare_advantage", "Humana Gold", Payer("medicare_advantage")),
        ("other", "Workers comp", Payer(None)),
        (None, None, Payer(None)),
    ],
)
def test_the_practice_payer_list_maps_to_a_plan_and_family(plan_type, name, payer):
    assert payer_for(plan_type, name) == payer


def test_audio_video_telehealth_billed_with_the_office_place_is_flagged():
    assert _flags("99214-95, I10", MEDICARE, "11") == [("telehealth_place", "risk", ("99214-95",))]
    assert _flags("99214-95, I10", MEDICARE, "10") == []
    assert _flags("99214-95, I10", MEDICARE, "02") == []
    assert _flags("99214-95, I10", MEDICARE, "22") == []
    assert _flags("99214, I10", MEDICARE, "10") == []


def test_audio_only_telehealth_needs_the_patient_at_home():
    assert _flags("99213-93", MEDICARE, "02") == [("audio_only_place", "denial", ("99213-93",))]
    assert _flags("99213-93", MEDICARE, "11") == [("audio_only_place", "denial", ("99213-93",))]
    assert _flags("99213-93", MEDICARE, "10") == []


def test_home_telehealth_flexibilities_run_through_december_31_2027():
    assert _flags("99214", MEDICARE, "10", date(2027, 12, 31)) == []
    assert _flags("99214", MEDICARE, "10", date(2028, 1, 3)) == [("home_telehealth_ended", "risk", ("99214",))]


def test_g2211_is_not_paid_when_the_visit_carries_modifier_25():
    assert _flags("99214-25, G2211, 20610, M17.11", MEDICARE) == [
        ("complexity_with_25", "denial", ("99214-25", "G2211"))
    ]
    assert _flags("99214, G2211, M17.11", MEDICARE) == []


@pytest.mark.parametrize("service", ["G0439", "G0402", "90471", "99497", "77067", "Q0091"])
def test_g2211_with_25_is_paid_beside_a_preventive_service_vaccine_or_wellness_visit(service):
    assert _flags(f"99214-25, G2211, {service}, Z00.00", MEDICARE) == []


def test_the_preventive_exception_starts_with_2025_dates_of_service():
    assert _flags("99214-25, G2211, G0439", MEDICARE, day=date(2024, 12, 31)) == [
        ("complexity_with_25", "denial", ("99214-25", "G2211"))
    ]


def test_g2211_with_a_home_visit_and_modifier_25():
    assert _flags("99349-25, G2211, 20610", MEDICARE) == [("complexity_with_25", "denial", ("99349-25", "G2211"))]


def test_from_2027_g2211_is_replaced_by_modifier_b1_with_the_same_25_limit():
    assert _flags("99214, G2211", MEDICARE, day=JANUARY_2027) == [("g2211_replaced", "denial", ("G2211",))]
    assert _flags("99214-25-B1, 20610", MEDICARE, day=JANUARY_2027) == [
        ("complexity_with_25", "denial", ("99214-25-B1",))
    ]
    assert _flags("99214-25-B1, G0439", MEDICARE, day=JANUARY_2027) == []
    assert _flags("99214-B1", MEDICARE, day=JANUARY_2027) == []


def test_cigna_level_4_and_5_visits_with_only_symptom_and_status_diagnoses_risk_a_downcode():
    assert _flags("99214, R51.9, Z00.00", CIGNA) == [("level_downcode_risk", "risk", ("99214",))]
    assert _flags("99245, R10.9", CIGNA) == [("level_downcode_risk", "risk", ("99245",))]
    assert _flags("99214, R51.9, E11.65", CIGNA) == []
    assert _flags("99213, R51.9", CIGNA) == []


def test_the_cigna_policy_spares_infants_and_other_payers_and_starts_october_2025():
    assert _flags("99214, R50.9", CIGNA, patient_age=0) == []
    assert _flags("99214, R50.9", CIGNA, patient_age=1) == [("level_downcode_risk", "risk", ("99214",))]
    assert _flags("99214, R50.9", Payer("commercial")) == []
    assert _flags("99214, R50.9", CIGNA, day=date(2025, 9, 30)) == []


def test_medicare_advantage_audio_only_diagnoses_do_not_count_for_risk_adjustment():
    assert _flags("99213-93, E11.65", ADVANTAGE, "10") == [("audio_only_risk_adjustment", "risk", ("99213-93",))]
    assert _flags("99213-93, E11.65", ADVANTAGE, "10", date(2025, 12, 31)) == []
    assert _flags("99213-95, E11.65", ADVANTAGE, "10") == []
    assert _flags("99213-93, E11.65", MEDICARE, "10") == []


def test_nursing_facility_initial_visits_and_incident_to():
    assert _flags("99306, I10", MEDICARE, "31") == [("nursing_initial_once", "reminder", ("99306",))]
    assert _flags("99309, I10", MEDICARE, "32", supervised_nonphysician=True) == [
        ("nursing_incident_to", "reminder", ("99309",))
    ]
    assert _flags("99306, I10", MEDICARE, "11") == []
    assert _flags("99309, I10", MEDICARE, "32") == []


def test_an_unknown_plan_has_no_payer_flags():
    assert _flags("99214-25, G2211, 99306", Payer(None), "31") == []
    assert _flags("99214-25, G2211", Payer("medicaid")) == []
