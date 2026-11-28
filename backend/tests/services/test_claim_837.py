from dataclasses import replace

import pytest

from app.services.claim_837 import Address, BillingProvider, Payer, Person, Subscriber, write_837p
from tests.claim_files import GROUP, MARISOL, PATIENT, SCREENING, VARGA, claim_file, self_claim

SELF_INSURED = [
    "ISA*00*          *00*          *ZZ*SUB123         *ZZ*OFFALLY        *261128*1430*^*00501*000000007*0*T*:",
    "GS*HC*SUB123*OFFALLY*20261128*1430*7*X*005010X222A1",
    "ST*837*0007*005010X222A1",
    "BHT*0019*00*F00DBABE*20261128*1430*CH",
    "NM1*41*2*LAKESIDE FAMILY MEDICINE*****46*SUB123",
    "PER*IC*DANA BILLER*TE*5555551234",
    "NM1*40*2*OFFICE ALLY*****46*OFFALLY",
    "HL*1**20*1",
    "PRV*BI*PXC*207Q00000X",
    "NM1*85*2*LAKESIDE FAMILY MEDICINE*****XX*1245319599",
    "N3*123 MAIN ST*SUITE 200",
    "N4*SPRINGFIELD*IL*627011234",
    "REF*EI*123456789",
    "HL*2*1*22*0",
    "SBR*P*18*******MB",
    "NM1*IL*1*REYES*MARISOL****MI*1EG4TE5MK72",
    "N3*9 ELM ST",
    "N4*SPRINGFIELD*IL*62704",
    "DMG*D8*19590312*F",
    "NM1*PR*2*MEDICARE PART B*****PI*MCRB",
    "CLM*1A2B3C4D-5E6F-7A8B-9*175***11:B:1*Y*A*Y*Y",
    "HI*ABK:E1165*ABF:I10",
    "NM1*82*1*VARGA*ELENA****XX*1234567893",
    "PRV*PE*PXC*207R00000X",
    "LX*1",
    "SV1*HC:99214:25*150*UN*1***1:2",
    "DTP*472*D8*20261125",
    "LX*2",
    "SV1*HC:96127*25*UN*2***1",
    "DTP*472*D8*20261125",
    "SE*29*0007",
    "GE*1*7",
    "IEA*1*000000007",
]


def _segments(text: str) -> list[str]:
    assert text.endswith("~")
    return text[:-1].split("~")


def test_a_self_insured_claim_follows_the_implementation_guide_segment_by_segment():
    text = write_837p(claim_file(self_claim()))

    assert _segments(text) == SELF_INSURED
    assert len(_segments(text)[0]) == 105


def test_a_dependent_gets_a_patient_level_under_the_subscriber():
    spouse = Subscriber(Person("Reyes", "Jose"), "XYZ1", "GRP 9", "01")
    claim = self_claim(subscriber=spouse, payer=Payer("Aetna", "60054", "CI"))

    found = _segments(write_837p(claim_file(claim)))

    start = found.index("HL*2*1*22*1")
    assert found[start : start + 11] == [
        "HL*2*1*22*1",
        "SBR*P**GRP 9******CI",
        "NM1*IL*1*REYES*JOSE****MI*XYZ1",
        "NM1*PR*2*AETNA*****PI*60054",
        "HL*3*2*23*0",
        "PAT*01",
        "NM1*QC*1*REYES*MARISOL",
        "N3*9 ELM ST",
        "N4*SPRINGFIELD*IL*62704",
        "DMG*D8*19590312*F",
        "CLM*1A2B3C4D-5E6F-7A8B-9*175***11:B:1*Y*A*Y*Y",
    ]


def test_claims_with_one_billing_provider_share_its_level_and_others_get_their_own():
    solo = BillingProvider("Elena Varga", VARGA, "1234567893", "123456789", "207R00000X", GROUP.address)
    second = self_claim(claim_ref="2A2B3C4D-5E6F-7A8B-9")
    third = self_claim(claim_ref="3A2B3C4D-5E6F-7A8B-9", billing=solo, rendering=None)

    found = _segments(write_837p(claim_file(self_claim(), second, third)))

    levels = [segment for segment in found if segment.startswith("HL*")]
    assert levels == ["HL*1**20*1", "HL*2*1*22*0", "HL*3*1*22*0", "HL*4**20*1", "HL*5*4*22*0"]
    assert "NM1*85*1*VARGA*ELENA****XX*1234567893" in found
    assert found.count("NM1*82*1*VARGA*ELENA****XX*1234567893") == 2


def test_names_and_addresses_keep_only_the_basic_character_set():
    patient = replace(
        PATIENT,
        person=Person("O'Neil-Smith", "José"),
        address=Address("12 Main St.*Apt~3", None, "Springfield", "IL", "62704"),
    )
    claim = self_claim(patient=patient, subscriber=Subscriber(patient.person, "1EG4TE5MK72", None, "18"))

    found = _segments(write_837p(claim_file(claim)))

    assert "NM1*IL*1*O'NEIL-SMITH*JOS****MI*1EG4TE5MK72" in found
    assert "N3*12 MAIN ST. APT 3" in found


def test_a_production_file_says_so_in_isa15():
    assert "*00501*000000042*0*P*:~" in write_837p(claim_file(self_claim(), control=42, usage="P"))


def test_a_file_needs_claims_with_one_to_fifty_lines():
    with pytest.raises(ValueError):
        write_837p(claim_file())
    with pytest.raises(ValueError):
        write_837p(claim_file(self_claim(lines=(SCREENING,) * 51)))
    with pytest.raises(ValueError):
        write_837p(claim_file(self_claim(lines=())))


def test_the_subscriber_member_id_cannot_carry_a_separator():
    with pytest.raises(ValueError):
        write_837p(claim_file(self_claim(subscriber=Subscriber(MARISOL, "1EG4*TE5", None, "18"))))
