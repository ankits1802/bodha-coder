import pytest

from app.services.claim_837 import Person, Subscriber, write_837p
from app.services.claim_837_check import check_837p, problems_837p
from app.services.x12 import X12Invalid
from tests.claim_files import claim_file, self_claim

VALID = write_837p(claim_file(self_claim()))


def _problems(old: str, new: str) -> list[str]:
    assert old in VALID
    return problems_837p(VALID.replace(old, new, 1))


def test_a_written_file_passes_every_check():
    spouse = Subscriber(Person("Reyes", "Jose"), "XYZ1", "GRP9", "01")
    assert problems_837p(VALID) == []
    assert problems_837p(write_837p(claim_file(self_claim(), self_claim(subscriber=spouse)))) == []
    check_837p(VALID)


def test_the_claim_total_must_equal_its_lines():
    assert _problems("*175***11:B:1", "*176***11:B:1") == [
        "CLM at segment 21: CLM02 does not equal the sum of the service line charges"
    ]


def test_npis_are_checked_with_the_luhn_digit():
    assert _problems("XX*1234567893", "XX*1234567890") == ["NM1 at segment 23: NM109 is not a valid NPI"]


def test_a_pointer_must_name_one_of_the_claim_diagnoses():
    assert _problems("UN*1***1:2~", "UN*1***1:3~") == [
        "SV1 at segment 26: SV107 must point to 1 to 4 of the claim's diagnoses"
    ]
    assert _problems("UN*1***1:2~", "UN*1***1:1~") == [
        "SV1 at segment 26: SV107 must point to 1 to 4 of the claim's diagnoses"
    ]


def test_the_billing_provider_needs_a_nine_digit_zip_and_an_ein():
    assert _problems("N4*SPRINGFIELD*IL*627011234", "N4*SPRINGFIELD*IL*62701") == [
        "N4 at segment 12: N403 must be a five or nine-digit ZIP code"
    ]
    assert _problems("REF*EI*123456789", "REF*EI*12345678") == [
        "REF at segment 13: REF02 must be an EIN of nine digits"
    ]


def test_codes_have_their_shapes():
    assert _problems("HI*ABK:E1165", "HI*ABK:E11.65") == [
        "HI at segment 22: HI01 must be ABK and an ICD-10-CM code without a dot"
    ]
    assert _problems("HC:99214:25", "HC:9921:25") == ["SV1 at segment 26: SV101 must be HC and a CPT or HCPCS code"]
    assert _problems("HC:99214:25", "HC:99214:255") == [
        "SV1 at segment 26: SV101 holds at most 4 two-character modifiers"
    ]
    assert _problems("DMG*D8*19590312*F", "DMG*D8*19590231*F") == ["DMG at segment 19: DMG02 must be a date (CCYYMMDD)"]
    assert _problems("*******MB~", "*******XX~") == ["SBR at segment 15: SBR09 is not a claim filing indicator"]


def test_the_envelope_names_the_professional_guide_and_a_usage():
    assert _problems("*0*T*:~", "*0*X*:~") == ["ISA at segment 1: ISA15 must be T (test) or P (production)"]
    assert "GS at segment 2: GS08 must be 005010X222A1" in _problems("*X*005010X222A1~ST", "*X*005010X223A2~ST")


def test_counts_and_control_numbers_are_checked_by_the_reader():
    assert _problems("SE*29*0007", "SE*28*0007") == ["SE counts 28 but there are 29"]
    assert _problems("GE*1*7~", "GE*1*8~") == ["GE control number 8 does not match 7"]


def test_the_hierarchy_must_point_to_earlier_levels():
    assert "HL at segment 14: HL02 must point to an earlier level 20" in _problems("HL*2*1*22*0", "HL*2*9*22*0")


def test_check_raises_with_the_problems():
    with pytest.raises(X12Invalid) as raised:
        check_837p(VALID.replace("XX*1234567893", "XX*1234567890", 1))
    assert raised.value.message == "the claim file failed its checks: NM1 at segment 23: NM109 is not a valid NPI"
