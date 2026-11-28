from dataclasses import replace

import pytest

from app.services.x12 import read_transactions
from app.services.x12_writer import Interchange, amount, composite, segment, text, write_interchange
from tests.claim_files import MADE

ENVELOPE = Interchange("ZZ", "SUB123", "30", "123456789", "T", 12345, MADE, "HC", "837", "005010X222A1")


def test_amounts_are_dollars_without_trailing_zeros():
    assert [amount(15000), amount(1250), amount(1205), amount(5), amount(0)] == ["150", "12.5", "12.05", "0.05", "0"]
    with pytest.raises(ValueError):
        amount(-1)


def test_text_is_upper_case_basic_characters_trimmed_to_its_limit():
    assert text("  mary   ann*o'brien~ ", 60) == "MARY ANN O'BRIEN"
    assert text("Lakeside Family Medicine", 8) == "LAKESIDE"
    assert text("Suite #4, Bldg (B)", 55) == "SUITE #4, BLDG (B)"


def test_segments_drop_trailing_empty_elements_and_refuse_separators():
    assert segment("SBR", "P", "18", "", "", "", "", "", "", "MB") == "SBR*P*18*******MB"
    assert segment("N3", "9 ELM ST", "") == "N3*9 ELM ST"
    assert composite("HC", "99214", "25", "", "") == "HC:99214:25"
    for bad in ("A*B", "A~B", "A^B", "A\nB"):
        with pytest.raises(ValueError):
            segment("REF", "EI", bad)
    with pytest.raises(ValueError):
        composite("HC", "992:14")


def test_an_interchange_counts_its_segments_and_repeats_its_control_numbers():
    written = write_interchange(ENVELOPE, ["BHT*0019*00*1*20261128*1430*CH"])

    assert written.split("~")[:3] == [
        "ISA*00*          *00*          *ZZ*SUB123         *30*123456789      *261128*1430*^*00501*000012345*0*T*:",
        "GS*HC*SUB123*123456789*20261128*1430*12345*X*005010X222A1",
        "ST*837*12345*005010X222A1",
    ]
    assert written.endswith("SE*3*12345~GE*1*12345~IEA*1*000012345~")
    assert len(read_transactions(written, code="837")[0].segments) == 3


def test_control_numbers_and_interchange_ids_stay_in_range():
    with pytest.raises(ValueError):
        write_interchange(replace(ENVELOPE, control_number=0), [])
    with pytest.raises(ValueError):
        write_interchange(replace(ENVELOPE, control_number=1_000_000_000), [])
    with pytest.raises(ValueError):
        write_interchange(replace(ENVELOPE, sender_id="A" * 16), [])
    assert "ST*837*0007*" in write_interchange(replace(ENVELOPE, control_number=7), [])
