from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner

SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
MD = "urn:oasis:names:tc:SAML:2.0:metadata"
DS = "http://www.w3.org/2000/09/xmldsig#"
EXCLUSIVE_C14N = "http://www.w3.org/2001/10/xml-exc-c14n#"
SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success"
REQUESTER = "urn:oasis:names:tc:SAML:2.0:status:Requester"
BEARER = "urn:oasis:names:tc:SAML:2.0:cm:bearer"
PASSWORD_CONTEXT = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
MFA_CONTEXT = "http://schemas.microsoft.com/claims/multipleauthn"
REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
IDP_ENTITY = "https://idp.lakeside.example.com/saml"
IDP_SSO_URL = "https://idp.lakeside.example.com/sso?tenant=lakeside"
NAMESPACES = {"samlp": SAMLP, "saml": SAML, "ds": DS}


@dataclass(frozen=True)
class IdpKeys:
    key: rsa.RSAPrivateKey
    certificate: x509.Certificate

    @property
    def compact(self) -> str:
        return base64.b64encode(self.certificate.public_bytes(Encoding.DER)).decode("ascii")

    @property
    def pem(self) -> str:
        return self.certificate.public_bytes(Encoding.PEM).decode("ascii")

    @property
    def sha256(self) -> str:
        return self.certificate.fingerprint(hashes.SHA256()).hex()


def idp_keys(*, common_name: str = "idp.lakeside.example.com", expired: bool = False) -> IdpKeys:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    starts, ends = (
        (now - timedelta(days=30), now - timedelta(days=1))
        if expired
        else (now - timedelta(days=1), now + timedelta(days=365))
    )
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(starts)
        .not_valid_after(ends)
        .sign(key, hashes.SHA256())
    )
    return IdpKeys(key, certificate)


@dataclass(frozen=True)
class Assertion:
    acs_url: str
    audience: str
    email: str = "anna@lakeside.example.com"
    name: str | None = "Anna Reyes"
    issuer: str = IDP_ENTITY
    in_response_to: str | None = None
    context_class: str = PASSWORD_CONTEXT
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    lifetime: timedelta = timedelta(minutes=5)
    not_before: datetime | None = None
    session_ends: datetime | None = None
    destination: str | None = None
    status: str = SUCCESS
    email_in_name_id: bool = True
    assertion_id: str = field(default_factory=lambda: "_a" + secrets.token_hex(16))
    response_id: str = field(default_factory=lambda: "_r" + secrets.token_hex(16))

    def answering(self, request_id: str | None) -> Assertion:
        return replace(self, in_response_to=request_id)


def instant(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _child(
    parent: etree._Element, namespace: str, name: str, text: str | None = None, **attributes: str
) -> etree._Element:
    element = etree.SubElement(parent, f"{{{namespace}}}{name}")
    for key, value in attributes.items():
        element.set(key, value)
    if text is not None:
        element.text = text
    return element


def _placeholder(parent: etree._Element) -> None:
    _child(parent, DS, "Signature", Id="placeholder")


def _subject(assertion_element: etree._Element, facts: Assertion) -> None:
    subject = _child(assertion_element, SAML, "Subject")
    name_id = facts.email if facts.email_in_name_id else "opaque-subject-1"
    _child(subject, SAML, "NameID", name_id, Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")
    confirmation = _child(subject, SAML, "SubjectConfirmation", Method=BEARER)
    data = {"Recipient": facts.acs_url, "NotOnOrAfter": instant(facts.issued_at + facts.lifetime)}
    if facts.in_response_to is not None:
        data["InResponseTo"] = facts.in_response_to
    if facts.not_before is not None:
        data["NotBefore"] = instant(facts.not_before)
    _child(confirmation, SAML, "SubjectConfirmationData", **data)


def _conditions(assertion_element: etree._Element, facts: Assertion) -> None:
    starts = facts.not_before or facts.issued_at - timedelta(seconds=30)
    ends = facts.issued_at + facts.lifetime
    conditions = _child(assertion_element, SAML, "Conditions", NotBefore=instant(starts), NotOnOrAfter=instant(ends))
    restriction = _child(conditions, SAML, "AudienceRestriction")
    _child(restriction, SAML, "Audience", facts.audience)


def _statements(assertion_element: etree._Element, facts: Assertion) -> None:
    authn = {"AuthnInstant": instant(facts.issued_at), "SessionIndex": "_s1"}
    if facts.session_ends is not None:
        authn["SessionNotOnOrAfter"] = instant(facts.session_ends)
    statement = _child(assertion_element, SAML, "AuthnStatement", **authn)
    context = _child(statement, SAML, "AuthnContext")
    _child(context, SAML, "AuthnContextClassRef", facts.context_class)
    attributes = _child(assertion_element, SAML, "AttributeStatement")
    values = {"email": facts.email, "displayName": facts.name}
    for attribute_name, value in values.items():
        if value is None:
            continue
        attribute = _child(attributes, SAML, "Attribute", Name=attribute_name)
        _child(attribute, SAML, "AttributeValue", value)


def response_tree(facts: Assertion, *, placeholder: bool = True) -> etree._Element:
    response = etree.Element(f"{{{SAMLP}}}Response", nsmap={"samlp": SAMLP, "saml": SAML, "ds": DS})
    response.set("ID", facts.response_id)
    response.set("Version", "2.0")
    response.set("IssueInstant", instant(facts.issued_at))
    response.set("Destination", facts.destination or facts.acs_url)
    if facts.in_response_to is not None:
        response.set("InResponseTo", facts.in_response_to)
    _child(response, SAML, "Issuer", facts.issuer)
    status = _child(response, SAMLP, "Status")
    _child(status, SAMLP, "StatusCode", Value=facts.status)
    assertion_element = _child(
        response, SAML, "Assertion", ID=facts.assertion_id, Version="2.0", IssueInstant=instant(facts.issued_at)
    )
    _child(assertion_element, SAML, "Issuer", facts.issuer)
    if placeholder:
        _placeholder(assertion_element)
    _subject(assertion_element, facts)
    _conditions(assertion_element, facts)
    _statements(assertion_element, facts)
    return response


def sign(root: etree._Element, keys: IdpKeys, reference_id: str, *, signer: XMLSigner | None = None) -> etree._Element:
    chosen = signer or XMLSigner(c14n_algorithm=EXCLUSIVE_C14N)
    return chosen.sign(root, key=keys.key, cert=[keys.certificate], reference_uri=reference_id, id_attribute="ID")


def signed_response(
    facts: Assertion, keys: IdpKeys, *, sign_assertion: bool = True, sign_response: bool = False
) -> etree._Element:
    root = response_tree(facts, placeholder=sign_assertion)
    if sign_assertion:
        root = sign(root, keys, facts.assertion_id)
    if sign_response:
        root = sign_whole_response(root, keys)
    return root


def sign_whole_response(root: etree._Element, keys: IdpKeys) -> etree._Element:
    issuer = root.find(f"{{{SAML}}}Issuer")
    assert issuer is not None
    placeholder = etree.Element(f"{{{DS}}}Signature")
    placeholder.set("Id", "placeholder")
    issuer.addnext(placeholder)
    return sign(root, keys, str(root.get("ID")))


def encoded(root: etree._Element) -> str:
    return base64.b64encode(etree.tostring(root)).decode("ascii")


def encoded_text(xml: bytes) -> str:
    return base64.b64encode(xml).decode("ascii")


def find(root: etree._Element, path: str) -> etree._Element:
    found = root.find(path, namespaces=NAMESPACES)
    assert found is not None, path
    return found


def idp_metadata(
    keys: tuple[IdpKeys, ...],
    *,
    entity_id: str = IDP_ENTITY,
    sso_url: str = IDP_SSO_URL,
    bindings: tuple[str, ...] = (POST, REDIRECT),
) -> bytes:
    root = etree.Element(f"{{{MD}}}EntityDescriptor", nsmap={"md": MD, "ds": DS})
    root.set("entityID", entity_id)
    descriptor = _child(root, MD, "IDPSSODescriptor", protocolSupportEnumeration=SAMLP)
    for pair in keys:
        key_descriptor = _child(descriptor, MD, "KeyDescriptor", use="signing")
        key_info = _child(key_descriptor, DS, "KeyInfo")
        data = _child(key_info, DS, "X509Data")
        _child(data, DS, "X509Certificate", pair.compact)
    for binding in bindings:
        _child(descriptor, MD, "SingleSignOnService", Binding=binding, Location=sso_url)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")
