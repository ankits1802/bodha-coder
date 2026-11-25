from __future__ import annotations

import pytest

from app.ai.cdi import with_undetermined_option
from app.ai.json_text import extract_json, parse_json_loose, render_json_template


def test_c_a_fenced_object_is_recovered() -> None:
    assert parse_json_loose('```json\n{"em": {"code": "99213"}}\n```') == {"em": {"code": "99213"}}


def test_c_an_object_with_prose_around_it_is_recovered() -> None:
    text = 'Sure, here is the review: {"em": {"code": "99213"}} Let me know if you need more.'
    assert parse_json_loose(text) == {"em": {"code": "99213"}}


def test_c_a_truncated_object_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_json_loose('{"em": {"code": "99213"}, "cdi": {"overallCDIScore": 7')


def test_c_a_leading_array_is_extracted_whole() -> None:
    assert extract_json("Codes: [1, 2] and nothing else") == "[1, 2]"


def test_a_template_slot_is_replaced_with_indented_json() -> None:
    assert render_json_template("A {{json .}} B", {"x": 1}) == 'A {\n  "x": 1\n} B'


def test_query_options_end_with_clinically_undetermined_and_stay_within_four() -> None:
    options = ["Type 1", "Type 2", "Type 2", " ", "Other", "Gestational", "Clinically Undetermined"]
    assert with_undetermined_option(options) == ["Type 1", "Type 2", "Other", "Clinically undetermined"]


def test_query_options_always_offer_the_undetermined_escape() -> None:
    assert with_undetermined_option(["Yes"]) == ["Yes", "Clinically undetermined"]
