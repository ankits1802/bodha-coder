import pytest

from app.services.ack_277 import ACCEPTED, PENDING, REJECTED, StatusLine, outcome_of, parse_277ca
from app.services.ack_999 import AckReason, parse_999
from app.services.x12 import X12Invalid
from tests.acknowledgments import ACCEPTED_CLAIM, ISA, REJECTED_CLAIM, ack_277, ack_999

FIRST, SECOND = "1A2B3C4D-5E6F-7A8B-9", "2A2B3C4D-5E6F-7A8B-9"


def test_an_accepted_999_names_the_group_it_acknowledges():
    (group,) = parse_999(ack_999(7, accepted=True))

    assert (group.group_control, group.receiver_id, group.status, group.accepted) == ("7", "SUB123", "A", True)
    assert [(item.control, item.accepted, item.reasons) for item in group.sets] == [("0007", True, ())]


def test_a_rejected_999_explains_the_segment_and_element_in_error():
    (group,) = parse_999(ack_999(7, accepted=False))

    assert group.accepted is False
    assert group.sets[0].reasons == (
        AckReason("IK3-8", "segment NM1 16 (loop 2010BA): segment has data element errors"),
        AckReason("IK4-1", "element 9 of segment NM1 16 (loop 2010BA): required data element missing"),
        AckReason("IK5-5", "transaction: one or more segments in error"),
    )


def test_a_999_for_something_other_than_claims_is_refused():
    with pytest.raises(X12Invalid):
        parse_999(ack_999(7, accepted=True).replace(b"AK1*HC*", b"AK1*HP*"))


def test_a_277ca_gives_each_claim_its_outcome_and_reason():
    (batch,) = parse_277ca(ack_277("F00DBABE", [(FIRST, ACCEPTED_CLAIM), (SECOND, REJECTED_CLAIM)]))

    assert (batch.batch_ref, batch.outcome) == ("F00DBABE", ACCEPTED)
    first, second = batch.claims
    assert (first.claim_ref, first.outcome, first.payer_claim_number) == (FIRST, ACCEPTED, "PAYER123")
    assert (second.claim_ref, second.outcome, second.payer_claim_number) == (SECOND, REJECTED, None)
    assert [line.reason() for line in second.statuses] == [
        AckReason("A7:562:85", "rejected for invalid information (status 562): billing provider npi invalid")
    ]


def test_a_277ca_batch_without_claims_carries_its_own_outcome():
    (batch,) = parse_277ca(ack_277("F00DBABE", []).replace(b"STC*A1:19:PR", b"STC*A3:24:PR"))

    assert (batch.outcome, batch.claims) == (REJECTED, ())
    assert batch.statuses[0].reason() == AckReason("A3:24:PR", "returned as unprocessable (status 24)")


def test_a_claim_without_a_reference_or_status_is_refused():
    with pytest.raises(X12Invalid):
        parse_277ca(ack_277("F00DBABE", [(FIRST, [])]))


def test_categories_decide_the_outcome_and_a_reject_action_always_rejects():
    def line(category: str, action: str = "") -> StatusLine:
        return StatusLine(category, "", "", action, "")

    assert outcome_of([line("A1")]) == ACCEPTED
    assert outcome_of([line("A2"), line("A7")]) == REJECTED
    assert outcome_of([line("E1")]) == PENDING
    assert outcome_of([line("A1", "U")]) == REJECTED
    assert outcome_of([]) == PENDING


def test_a_file_that_is_not_x12_is_refused():
    with pytest.raises(X12Invalid):
        parse_999(b"\xff\xfe not text")
    with pytest.raises(X12Invalid):
        parse_277ca((ISA + "GS*HN*X*Y*20261128*1500*1*X*005010X214~GE*0*1~IEA*1*000000101~").encode())
