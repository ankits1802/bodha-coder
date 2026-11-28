from __future__ import annotations

import base64
import binascii
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography import x509
from lxml import etree

from app.adapters.saml_metadata import ServiceProvider, load_certificate
from app.adapters.saml_signature import ASSERTION_SIGNATURE, RESPONSE_SIGNATURE, signed_element
from app.adapters.saml_xml import DS, SAML, SAMLP, UnsafeXml, ids_in, parse_xml, tag, text_of

__all__ = [
    "CLOCK_SKEW",
    "MAX_ASSERTION_AGE",
    "ResponseRules",
    "SamlIdentity",
    "SamlRefused",
    "read_response",
]

CLOCK_SKEW = timedelta(minutes=2)
MAX_ASSERTION_AGE = timedelta(minutes=10)
MAX_ENCODED_CHARS = 1_400_000
SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success"
BEARER = "urn:oasis:names:tc:SAML:2.0:cm:bearer"
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")
EMAIL_LENGTH = 254
NAME_LENGTH = 120


class SamlRefused(Exception):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass(frozen=True)
class ResponseRules:
    sp: ServiceProvider
    idp_entity_id: str
    certificates: tuple[str, ...]
    request_id: str | None
    email_attribute: str | None
    name_attribute: str | None
    now: datetime


@dataclass(frozen=True)
class SamlIdentity:
    assertion_id: str
    issuer: str
    email: str
    name: str
    context_class: str | None
    keep_until: datetime


def read_response(encoded: str, rules: ResponseRules) -> SamlIdentity:
    document = _decoded(encoded)
    root = _parsed(document)
    _check_status(root)
    assertion = _single_assertion(root)
    _check_structure(root, assertion)
    trusted = _trusted_assertion(document, root, assertion, rules.certificates)
    _check_response(root, rules)
    return _identity(trusted, rules)


def _decoded(encoded: str) -> bytes:
    compact = "".join(encoded.split())
    if not compact or len(compact) > MAX_ENCODED_CHARS:
        raise SamlRefused("malformed", "the identity provider's answer is empty or too large")
    try:
        return base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as error:
        raise SamlRefused("malformed", "the identity provider's answer is not base64") from error


def _parsed(document: bytes) -> etree._Element:
    try:
        root = parse_xml(document)
    except UnsafeXml as error:
        raise SamlRefused("malformed", f"the identity provider's answer is refused: {error}") from error
    if root.tag != tag(SAMLP, "Response") or root.get("Version") != "2.0" or not root.get("ID"):
        raise SamlRefused("malformed", "the identity provider's answer is not a SAML 2.0 response")
    return root


def _check_status(root: etree._Element) -> None:
    code = root.find(f"{tag(SAMLP, 'Status')}/{tag(SAMLP, 'StatusCode')}")
    if code is None or code.get("Value") != SUCCESS:
        raise SamlRefused("status", "the identity provider did not sign the person in")


def _single_assertion(root: etree._Element) -> etree._Element:
    if next(root.iter(tag(SAML, "EncryptedAssertion")), None) is not None:
        raise SamlRefused("encrypted", "encrypted assertions are not accepted")
    assertions = list(root.iter(tag(SAML, "Assertion")))
    if len(assertions) != 1 or assertions[0].getparent() is not root or not assertions[0].get("ID"):
        raise SamlRefused("wrapped", "the response must hold exactly one assertion directly")
    return assertions[0]


def _check_structure(root: etree._Element, assertion: etree._Element) -> None:
    ids = ids_in(root)
    if len(ids) != len(set(ids)):
        raise SamlRefused("wrapped", "the response repeats an ID")
    for signature in root.iter(tag(DS, "Signature")):
        holder = signature.getparent()
        if holder is not root and holder is not assertion:
            raise SamlRefused("wrapped", "a signature sits in an unexpected place")
    if len(root.findall(tag(DS, "Signature"))) > 1 or len(assertion.findall(tag(DS, "Signature"))) > 1:
        raise SamlRefused("wrapped", "a part of the response carries more than one signature")


def _trusted_assertion(
    document: bytes, root: etree._Element, assertion: etree._Element, certificates: tuple[str, ...]
) -> etree._Element:
    keys = [load_certificate(compact) for compact in certificates]
    response_signed = root.find(tag(DS, "Signature")) is not None
    assertion_signed = assertion.find(tag(DS, "Signature")) is not None
    if not (response_signed or assertion_signed):
        raise SamlRefused("unsigned", "the response is not signed")
    trusted: etree._Element | None = None
    if response_signed:
        response = _verified(document, RESPONSE_SIGNATURE, keys, tag(SAMLP, "Response"), root.get("ID"))
        inner = response.findall(tag(SAML, "Assertion"))
        if len(inner) != 1:
            raise SamlRefused("wrapped", "the signed response must hold exactly one assertion")
        trusted = inner[0]
    if assertion_signed:
        signed = _verified(document, ASSERTION_SIGNATURE, keys, tag(SAML, "Assertion"), assertion.get("ID"))
        trusted = signed if trusted is None else trusted
    if trusted is None or trusted.get("ID") != assertion.get("ID"):
        raise SamlRefused("wrapped", "the signed assertion is not the one in the response")
    return trusted


def _verified(
    document: bytes, location: str, keys: list[x509.Certificate], expected_tag: str, expected_id: str | None
) -> etree._Element:
    signed = signed_element(document, location, keys)
    if signed is None:
        raise SamlRefused("signature", "the response is not signed with the identity provider's certificate")
    if signed.tag != expected_tag or not expected_id or signed.get("ID") != expected_id:
        raise SamlRefused("wrapped", "the signature covers a different part of the response")
    return signed


def _check_response(root: etree._Element, rules: ResponseRules) -> None:
    destination = root.get("Destination")
    if destination is not None and destination != rules.sp.acs_url:
        raise SamlRefused("destination", "the response was sent to another address")
    issuer = root.find(tag(SAML, "Issuer"))
    if issuer is not None and text_of(issuer) != rules.idp_entity_id:
        raise SamlRefused("issuer", "the response comes from another identity provider")
    _check_in_response_to(root.get("InResponseTo"), rules.request_id, required=False)


def _check_in_response_to(found: str | None, expected: str | None, *, required: bool) -> None:
    if expected is None:
        if found is not None:
            raise SamlRefused("request", "the response answers a sign-in this browser did not start")
        return
    if found is None:
        if required:
            raise SamlRefused("request", "the response does not answer this sign-in")
        return
    if not hmac.compare_digest(found.encode(), expected.encode()):
        raise SamlRefused("request", "the response answers another sign-in")


def _identity(assertion: etree._Element, rules: ResponseRules) -> SamlIdentity:
    issuer = text_of(assertion.find(tag(SAML, "Issuer")))
    if assertion.get("Version") != "2.0" or issuer != rules.idp_entity_id:
        raise SamlRefused("issuer", "the assertion comes from another identity provider")
    issued = _instant(assertion.get("IssueInstant"))
    _check_window(not_before=issued, not_on_or_after=issued + MAX_ASSERTION_AGE, now=rules.now)
    subject = assertion.find(tag(SAML, "Subject"))
    if subject is None:
        raise SamlRefused("malformed", "the assertion names no subject")
    limits = [_bearer_confirmation(subject, rules), issued + MAX_ASSERTION_AGE]
    conditions_until = _conditions(assertion, rules)
    if conditions_until is not None:
        limits.append(conditions_until)
    return SamlIdentity(
        assertion_id=str(assertion.get("ID")),
        issuer=issuer,
        email=_email(assertion, subject, rules.email_attribute),
        name=_attribute_value(assertion, rules.name_attribute)[:NAME_LENGTH] if rules.name_attribute else "",
        context_class=_authn_context(assertion, rules.now),
        keep_until=min(limits) + CLOCK_SKEW,
    )


def _bearer_confirmation(subject: etree._Element, rules: ResponseRules) -> datetime:
    problems: list[SamlRefused] = []
    for confirmation in subject.findall(tag(SAML, "SubjectConfirmation")):
        if confirmation.get("Method") != BEARER:
            continue
        try:
            return _confirmed_until(confirmation.find(tag(SAML, "SubjectConfirmationData")), rules)
        except SamlRefused as problem:
            problems.append(problem)
    if problems:
        raise problems[0]
    raise SamlRefused("recipient", "the assertion has no bearer confirmation")


def _confirmed_until(data: etree._Element | None, rules: ResponseRules) -> datetime:
    if data is None or data.get("Recipient") != rules.sp.acs_url:
        raise SamlRefused("recipient", "the assertion was meant for another address")
    _check_in_response_to(data.get("InResponseTo"), rules.request_id, required=True)
    until = _instant(data.get("NotOnOrAfter"))
    starts = data.get("NotBefore")
    _check_window(not_before=_instant(starts) if starts else None, not_on_or_after=until, now=rules.now)
    return until


def _conditions(assertion: etree._Element, rules: ResponseRules) -> datetime | None:
    conditions = assertion.find(tag(SAML, "Conditions"))
    if conditions is None:
        raise SamlRefused("audience", "the assertion names no audience")
    starts, ends = conditions.get("NotBefore"), conditions.get("NotOnOrAfter")
    until = _instant(ends) if ends else None
    _check_window(not_before=_instant(starts) if starts else None, not_on_or_after=until, now=rules.now)
    restrictions = conditions.findall(tag(SAML, "AudienceRestriction"))
    if not restrictions:
        raise SamlRefused("audience", "the assertion names no audience")
    for restriction in restrictions:
        audiences = [text_of(audience) for audience in restriction.findall(tag(SAML, "Audience"))]
        if rules.sp.entity_id not in audiences:
            raise SamlRefused("audience", "the assertion is meant for another service")
    return until


def _check_window(*, not_before: datetime | None, not_on_or_after: datetime | None, now: datetime) -> None:
    if not_before is not None and not_before > now + CLOCK_SKEW:
        raise SamlRefused("not_yet_valid", "the assertion is not valid yet")
    if not_on_or_after is not None and now - CLOCK_SKEW >= not_on_or_after:
        raise SamlRefused("expired", "the assertion has expired")


def _authn_context(assertion: etree._Element, now: datetime) -> str | None:
    statements = assertion.findall(tag(SAML, "AuthnStatement"))
    if not statements:
        raise SamlRefused("malformed", "the assertion has no authentication statement")
    for statement in statements:
        ends = statement.get("SessionNotOnOrAfter")
        if ends and _instant(ends) <= now:
            raise SamlRefused("expired", "the identity provider's session has ended")
    reference = statements[0].find(f"{tag(SAML, 'AuthnContext')}/{tag(SAML, 'AuthnContextClassRef')}")
    return text_of(reference) or None


def _email(assertion: etree._Element, subject: etree._Element, attribute: str | None) -> str:
    raw = _attribute_value(assertion, attribute) if attribute else text_of(subject.find(tag(SAML, "NameID")))
    address = raw.strip().lower()
    if len(address) > EMAIL_LENGTH or not EMAIL.fullmatch(address):
        raise SamlRefused("email", "the assertion carries no usable email address")
    return address


def _attribute_value(assertion: etree._Element, name: str | None) -> str:
    path = f"{tag(SAML, 'AttributeStatement')}/{tag(SAML, 'Attribute')}"
    for attribute in assertion.findall(path):
        if attribute.get("Name") != name:
            continue
        for value in attribute.findall(tag(SAML, "AttributeValue")):
            if found := text_of(value):
                return found
    return ""


def _instant(value: str | None) -> datetime:
    if not value:
        raise SamlRefused("malformed", "the assertion leaves out a time")
    try:
        moment = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise SamlRefused("malformed", "the assertion holds a time it cannot read") from error
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
