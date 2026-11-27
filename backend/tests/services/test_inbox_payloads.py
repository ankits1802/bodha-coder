import pytest

from app.api.responses.inbox import InboxPayload
from app.models import INBOX_KINDS
from app.services.inbox import PAYLOAD_KEYS, Notice, checked_payload


def test_every_inbox_kind_names_the_payload_keys_it_may_carry():
    assert set(PAYLOAD_KEYS) == set(INBOX_KINDS)


def test_the_response_declares_every_payload_key_and_nothing_else():
    assert {key for keys in PAYLOAD_KEYS.values() for key in keys} == set(InboxPayload.model_fields)


def test_compliance_returned_is_ready_for_a_later_writer():
    assert checked_payload(Notice("compliance_returned", "Cam Compliance", payload={"reason": "documentation"})) == {
        "reason": "documentation"
    }


@pytest.mark.parametrize(
    ("notice", "message"),
    [
        (Notice("mentioned", payload={"patient_name": "Marisol Reyes"}), "patient_name is not allowed for mentioned"),
        (Notice("plan_ending", payload={"ends_on": "x" * 65}), "longer than 64 characters"),
        (Notice("signed_in"), "signed_in is not an inbox kind"),
    ],
)
def test_a_payload_outside_the_allowed_keys_is_refused(notice, message):
    with pytest.raises(ValueError, match=message):
        checked_payload(notice)
