import pytest

from app.codes.em import EM_FAMILIES, compare_em, describe_em, is_em_code
from app.codes.modifiers import allowed_modifiers, modifier_meaning


@pytest.mark.parametrize(
    ("billed", "supported", "direction", "difference"),
    [
        ("99236", "99234", "lower", 2),
        ("99234", "99235", "raise", -1),
        ("99223", "99235", "replace", 0),
        ("99291", "99291", "keep", 0),
        ("99285", "99291", "replace", 0),
    ],
)
def test_same_day_and_critical_care_compare_within_their_family(billed, supported, direction, difference):
    comparison = compare_em(billed, supported)
    assert (comparison.direction, comparison.level_difference) == (direction, difference)


def test_same_day_codes_carry_the_cpt_mdm_levels_and_times():
    family = next(item for item in EM_FAMILIES if item.id == "inpatient_same_day")
    assert [(level.code, level.mdm, level.minutes) for level in family.levels] == [
        ("99234", "Low", "45"),
        ("99235", "Moderate", "70"),
        ("99236", "High", "85"),
    ]
    assert describe_em("99235") == "Hospital inpatient or observation, admitted and discharged the same date · Moderate"


def test_critical_care_is_time_only_with_99292_as_its_add_on():
    family = next(item for item in EM_FAMILIES if item.id == "critical_care")
    assert [(level.code, level.mdm, level.minutes) for level in family.levels] == [("99291", "", "30-74")]
    assert [level.code for level in family.add_ons] == ["99292"]
    assert describe_em("99291") == "Critical care"
    assert is_em_code("99292") is False


def test_visit_and_procedure_codes_accept_different_modifiers():
    assert "25" in allowed_modifiers("99214")
    assert "59" not in allowed_modifiers("99214")
    assert "XS" in allowed_modifiers("20610")
    assert modifier_meaning("99214", "95") == "Audio-video telehealth"
    assert modifier_meaning("20610", "25") is None
