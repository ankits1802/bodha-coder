import base64
from datetime import UTC, datetime, timedelta

import pytest
from lxml import etree
from signxml import XMLSigner

from app.adapters.saml_metadata import ServiceProvider
from app.adapters.saml_response import ResponseRules, SamlRefused, read_response
from tests.saml_idp import (
    DS,
    EXCLUSIVE_C14N,
    MFA_CONTEXT,
    PASSWORD_CONTEXT,
    REQUESTER,
    SAML,
    SAMLP,
    Assertion,
    encoded,
    encoded_text,
    find,
    response_tree,
    sign,
    sign_whole_response,
    signed_response,
)

SP = ServiceProvider("https://app.test/api/auth/saml/c-1/metadata", "https://app.test/api/auth/saml/c-1/acs")
REQUEST = "_request-1"
SKEW = timedelta(minutes=2)


class Sha1Signer(XMLSigner):
    def check_deprecated_methods(self) -> None:
        return None


def facts(**changes) -> Assertion:
    return Assertion(**{"acs_url": SP.acs_url, "audience": SP.entity_id, "in_response_to": REQUEST, **changes})


def rules(*keys, request_id: str | None = REQUEST, email_attribute: str | None = None) -> ResponseRules:
    return ResponseRules(
        sp=SP,
        idp_entity_id="https://idp.lakeside.example.com/saml",
        certificates=tuple(pair.compact for pair in keys),
        request_id=request_id,
        email_attribute=email_attribute,
        name_attribute="displayName",
        now=datetime.now(UTC),
    )


def refusal(value: str, given: ResponseRules) -> str:
    with pytest.raises(SamlRefused) as caught:
        read_response(value, given)
    return caught.value.reason


def to_second(moment: datetime) -> datetime:
    return moment.replace(microsecond=0)


def test_a_signed_assertion_gives_the_person_and_how_long_to_keep_its_id(idp):
    sent = facts(context_class=MFA_CONTEXT)
    identity = read_response(encoded(signed_response(sent, idp)), rules(idp))
    assert (identity.email, identity.name, identity.context_class) == (
        "anna@lakeside.example.com",
        "Anna Reyes",
        MFA_CONTEXT,
    )
    assert (identity.assertion_id, identity.issuer) == (sent.assertion_id, "https://idp.lakeside.example.com/saml")
    assert identity.keep_until == to_second(sent.issued_at) + timedelta(minutes=5) + SKEW


def test_a_response_signed_only_at_the_top_is_accepted(idp):
    root = signed_response(facts(), idp, sign_assertion=False, sign_response=True)
    assert read_response(encoded(root), rules(idp)).email == "anna@lakeside.example.com"


def test_when_both_parts_are_signed_both_signatures_must_hold(idp):
    root = signed_response(facts(), idp, sign_response=True)
    assert read_response(encoded(root), rules(idp)).email == "anna@lakeside.example.com"
    value = find(root, "saml:Assertion/ds:Signature/ds:SignatureValue")
    value.text = base64.b64encode(b"\x00" * 256).decode()
    assert refusal(encoded(root), rules(idp)) == "signature"


def test_an_unsigned_response_is_refused(idp):
    assert refusal(encoded(response_tree(facts(), placeholder=False)), rules(idp)) == "unsigned"


def test_only_the_pinned_certificates_are_trusted_and_either_of_two_may_sign(idp, next_idp, stranger_idp):
    assert refusal(encoded(signed_response(facts(), stranger_idp)), rules(idp)) == "signature"
    rolled = read_response(encoded(signed_response(facts(), next_idp)), rules(idp, next_idp))
    assert rolled.email == "anna@lakeside.example.com"
    assert refusal(encoded(signed_response(facts(), stranger_idp)), rules(idp, next_idp)) == "signature"


def test_an_expired_pinned_certificate_no_longer_verifies(expired_idp):
    assert refusal(encoded(signed_response(facts(), expired_idp)), rules(expired_idp)) == "signature"


def test_a_sha1_signature_is_refused(idp):
    sent = facts()
    signer = Sha1Signer(signature_algorithm="rsa-sha1", digest_algorithm="sha1", c14n_algorithm=EXCLUSIVE_C14N)
    signed = sign(response_tree(sent), idp, sent.assertion_id, signer=signer)
    assert refusal(encoded(signed), rules(idp)) == "signature"


def test_changing_the_signed_email_breaks_the_signature(idp):
    root = signed_response(facts(), idp)
    find(root, "saml:Assertion/saml:Subject/saml:NameID").text = "mallory@lakeside.example.com"
    assert refusal(encoded(root), rules(idp)) == "signature"


def test_a_comment_inside_the_email_cannot_shorten_what_was_signed(idp):
    root = signed_response(facts(email="anna@lakeside.example.com.evil.test"), idp)
    name_id = find(root, "saml:Assertion/saml:Subject/saml:NameID")
    name_id.text = "anna@lakeside.example.com"
    hidden = etree.Comment("hidden")
    hidden.tail = ".evil.test"
    name_id.append(hidden)
    assert read_response(encoded(root), rules(idp)).email == "anna@lakeside.example.com.evil.test"


def _evil_assertion() -> etree._Element:
    evil = response_tree(facts(email="mallory@lakeside.example.com", assertion_id="_evil"), placeholder=False)
    return find(evil, "saml:Assertion")


def test_a_second_unsigned_assertion_beside_the_signed_one_is_refused(idp):
    root = signed_response(facts(), idp)
    root.append(_evil_assertion())
    assert refusal(encoded(root), rules(idp)) == "wrapped"


def test_a_signed_assertion_hidden_in_extensions_behind_a_forged_one_is_refused(idp):
    root = signed_response(facts(), idp)
    signed = find(root, "saml:Assertion")
    root.remove(signed)
    extensions = etree.SubElement(root, f"{{{SAMLP}}}Extensions")
    extensions.append(signed)
    root.append(_evil_assertion())
    assert refusal(encoded(root), rules(idp)) == "wrapped"


def test_a_signed_response_wrapped_inside_a_forged_response_is_refused(idp):
    original = signed_response(facts(), idp, sign_assertion=False, sign_response=True)
    forged = response_tree(
        facts(email="mallory@lakeside.example.com", response_id="_forged", assertion_id="_f"), placeholder=False
    )
    forged.append(original)
    assert refusal(encoded(forged), rules(idp)) == "wrapped"


def test_a_signature_on_the_response_that_covers_only_the_assertion_is_refused(idp):
    sent = facts()
    root = response_tree(sent, placeholder=False)
    placeholder = etree.Element(f"{{{DS}}}Signature")
    placeholder.set("Id", "placeholder")
    find(root, "saml:Issuer").addnext(placeholder)
    assert refusal(encoded(sign(root, idp, sent.assertion_id)), rules(idp)) == "wrapped"


def test_a_repeated_id_is_refused(idp):
    sent = facts()
    root = signed_response(sent, idp)
    extensions = etree.SubElement(root, f"{{{SAMLP}}}Extensions")
    extensions.set("ID", sent.assertion_id)
    assert refusal(encoded(root), rules(idp)) == "wrapped"


def test_a_signature_moved_deeper_into_the_assertion_is_refused(idp):
    root = signed_response(facts(), idp)
    signature = find(root, "saml:Assertion/ds:Signature")
    find(root, "saml:Assertion/saml:Subject").append(signature)
    assert refusal(encoded(root), rules(idp)) == "wrapped"


@pytest.mark.parametrize(
    "document",
    [
        b'<!DOCTYPE r [<!ENTITY x "y">]><samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">'
        b"&x;</samlp:Response>",
        b'<!DOCTYPE r SYSTEM "http://evil.test/r.dtd"><r/>',
        b"<samlp:Response xmlns:samlp='urn:oasis:names:tc:SAML:2.0:protocol'",
        b"<Response Version='2.0' ID='_x'/>",
    ],
)
def test_declarations_entities_and_other_documents_are_refused_before_any_check(idp, document):
    assert refusal(encoded_text(document), rules(idp)) == "malformed"


def test_text_that_is_not_base64_is_refused(idp):
    assert refusal("not base64 at all!", rules(idp)) == "malformed"


def test_a_failed_status_is_refused(idp):
    assert refusal(encoded(signed_response(facts(status=REQUESTER), idp)), rules(idp)) == "status"


def test_an_encrypted_assertion_is_refused(idp):
    root = response_tree(facts(), placeholder=False)
    root.remove(find(root, "saml:Assertion"))
    etree.SubElement(root, f"{{{SAML}}}EncryptedAssertion")
    assert refusal(encoded(root), rules(idp)) == "encrypted"


def test_the_issuer_must_be_the_configured_identity_provider(idp):
    assert refusal(encoded(signed_response(facts(issuer="https://idp.elsewhere.test"), idp)), rules(idp)) == "issuer"
    root = signed_response(facts(), idp)
    find(root, "saml:Issuer").text = "https://idp.elsewhere.test"
    assert refusal(encoded(root), rules(idp)) == "issuer"


def test_the_assertion_must_name_this_service_as_its_audience(idp):
    sent = facts(audience="https://another-service.test/saml")
    assert refusal(encoded(signed_response(sent, idp)), rules(idp)) == "audience"


def test_destination_and_recipient_must_be_this_service_address(idp):
    elsewhere = "https://another-service.test/acs"
    assert refusal(encoded(signed_response(facts(destination=elsewhere), idp)), rules(idp)) == "destination"
    sent = facts(acs_url=elsewhere, destination=SP.acs_url)
    assert refusal(encoded(signed_response(sent, idp)), rules(idp)) == "recipient"


def test_the_response_must_answer_the_request_this_browser_started(idp):
    assert refusal(encoded(signed_response(facts(in_response_to="_other"), idp)), rules(idp)) == "request"
    assert refusal(encoded(signed_response(facts(in_response_to=None), idp)), rules(idp)) == "request"
    unexpected = rules(idp, request_id=None)
    assert refusal(encoded(signed_response(facts(), idp)), unexpected) == "request"
    unsolicited = read_response(encoded(signed_response(facts(in_response_to=None), idp)), unexpected)
    assert unsolicited.email == "anna@lakeside.example.com"


def test_times_are_checked_with_two_minutes_of_skew(idp):
    now = datetime.now(UTC)
    early = read_response(encoded(signed_response(facts(issued_at=now + timedelta(seconds=90)), idp)), rules(idp))
    assert early.email == "anna@lakeside.example.com"
    cases = {
        "not_yet_valid": facts(issued_at=now + timedelta(minutes=4)),
        "expired": facts(issued_at=now - timedelta(minutes=20), lifetime=timedelta(hours=1)),
    }
    for reason, sent in cases.items():
        assert refusal(encoded(signed_response(sent, idp)), rules(idp)) == reason
    ended = facts(issued_at=now - timedelta(minutes=8), lifetime=timedelta(minutes=5))
    assert refusal(encoded(signed_response(ended, idp)), rules(idp)) == "expired"
    future = facts(not_before=now + timedelta(minutes=10))
    assert refusal(encoded(signed_response(future, idp)), rules(idp)) == "not_yet_valid"
    closed = facts(session_ends=now - timedelta(minutes=1))
    assert refusal(encoded(signed_response(closed, idp)), rules(idp)) == "expired"


def test_the_email_comes_from_the_mapped_attribute_or_else_the_name_id(idp):
    sent = facts(email_in_name_id=False)
    mapped = read_response(encoded(signed_response(sent, idp)), rules(idp, email_attribute="email"))
    assert mapped.email == "anna@lakeside.example.com"
    assert refusal(encoded(signed_response(sent, idp)), rules(idp)) == "email"
    assert refusal(encoded(signed_response(facts(), idp)), rules(idp, email_attribute="mail")) == "email"


def test_the_password_context_is_reported_as_is(idp):
    identity = read_response(encoded(signed_response(facts(), idp)), rules(idp))
    assert identity.context_class == PASSWORD_CONTEXT


def test_a_signed_response_whose_destination_was_changed_is_refused(idp):
    signed = sign_whole_response(response_tree(facts(), placeholder=False), idp)
    signed.set("Destination", "https://another-service.test/acs")
    assert refusal(encoded(signed), rules(idp)) == "signature"
