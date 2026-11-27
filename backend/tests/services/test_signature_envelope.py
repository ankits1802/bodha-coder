import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.services.signature_envelope import (
    CODE_ALPHABET,
    EnvelopeFacts,
    SignerIdentity,
    canonical_json,
    envelope_text,
    new_verification_code,
    normal_code,
    utc_text,
)

SIGNED_AT = datetime(2026, 11, 28, 9, 30, 15, 250000, tzinfo=UTC)
FACTS = EnvelopeFacts(
    event="approval",
    practice_id="p-1",
    note_id="n-1",
    record_id="r-1",
    statement="I approve this claim as coded from the documentation.",
    signer=SignerIdentity("user", "u-1", "Cora Coder", "coder", "Cora Coder"),
    signature_sha256="a" * 64,
    document_sha256="b" * 64,
    content_sha256="c" * 64,
    signed_at=SIGNED_AT,
    ip="127.0.0.1",
    user_agent="Safari",
)
EXPECTED_ENVELOPE = (
    '{"content_sha256":"' + "c" * 64 + '","document_sha256":"' + "b" * 64 + '","event":"approval",'
    '"ip":"127.0.0.1","note_id":"n-1","practice_id":"p-1","record_id":"r-1",'
    '"signature_sha256":"' + "a" * 64 + '","signed_at":"2026-11-28T09:30:15.250000Z",'
    '"signer":{"id":"u-1","kind":"user","name":"Cora Coder","title":"coder","typed_name":"Cora Coder"},'
    '"statement":"I approve this claim as coded from the documentation.","user_agent":"Safari","version":1}'
)


def test_canonical_json_sorts_keys_drops_whitespace_and_keeps_unicode():
    assert canonical_json({"b": 1, "a": ["é", None, True]}) == '{"a":["é",null,true],"b":1}'.encode()


def test_canonical_json_refuses_values_that_have_no_single_form():
    with pytest.raises(ValueError):
        canonical_json({"amount": float("nan")})


def test_the_envelope_is_the_canonical_form_of_every_signed_fact():
    assert envelope_text(FACTS).decode() == EXPECTED_ENVELOPE
    assert hashlib.sha256(envelope_text(FACTS)).hexdigest() == hashlib.sha256(EXPECTED_ENVELOPE.encode()).hexdigest()


def test_the_same_moment_in_another_zone_gives_the_same_envelope():
    elsewhere = SIGNED_AT.astimezone(timezone(timedelta(hours=-7)))
    moved = EnvelopeFacts(**{**FACTS.__dict__, "signed_at": elsewhere})
    assert envelope_text(moved) == envelope_text(FACTS)


def test_any_changed_fact_changes_the_envelope():
    renamed = EnvelopeFacts(**{**FACTS.__dict__, "statement": "I approve."})
    assert envelope_text(renamed) != envelope_text(FACTS)


def test_utc_text_refuses_a_time_without_a_zone():
    assert utc_text(SIGNED_AT) == "2026-11-28T09:30:15.250000Z"
    with pytest.raises(ValueError):
        utc_text(datetime(2026, 11, 28, 9, 30))


def test_verification_codes_are_three_groups_of_four_unambiguous_letters():
    code = new_verification_code()
    groups = code.split("-")
    assert [len(group) for group in groups] == [4, 4, 4]
    assert all(letter in CODE_ALPHABET for letter in "".join(groups))
    assert not set("01ILOU") & set(code)


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("abcd-efgh-jkmn", "ABCD-EFGH-JKMN"),
        (" ABCD EFGH JKMN ", "ABCD-EFGH-JKMN"),
        ("ABCDEFGHJKMN", "ABCD-EFGH-JKMN"),
        ("ABCD-EFGH-JKM", None),
        ("ABCD-EFGH-JKM0", None),
        ("", None),
    ],
)
def test_typed_codes_are_read_without_case_spaces_or_dashes(typed, expected):
    assert normal_code(typed) == expected
