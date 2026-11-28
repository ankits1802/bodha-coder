from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from lxml import etree

from app.adapters.saml_xml import DS, MD, SAMLP, UnsafeXml, parse_xml, tag, text_of
from app.core.errors import Invalid

__all__ = [
    "EMAIL_FORMAT",
    "MAX_CERTIFICATES",
    "POST_BINDING",
    "REDIRECT_BINDING",
    "SPEC_ENTITY_ID_LENGTH",
    "CertificateFacts",
    "IdpMetadata",
    "ServiceProvider",
    "certificate_facts",
    "checked_entity_id",
    "checked_sso_url",
    "load_certificate",
    "normal_certificate",
    "read_idp_metadata",
    "sp_metadata_xml",
]

REDIRECT_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
POST_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
EMAIL_FORMAT = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
SPEC_ENTITY_ID_LENGTH = 1024
MAX_CERTIFICATES = 4
SECURE_SCHEME = "https"
SIGNING_USES = (None, "signing")
PEM_LINE = re.compile(r"-----(BEGIN|END) CERTIFICATE-----")
CONTROL = re.compile(r"[\x00-\x20\x7f]")
NOT_METADATA = "the file is not SAML metadata"


@dataclass(frozen=True)
class IdpMetadata:
    entity_id: str
    sso_url: str
    certificates: tuple[str, ...]


@dataclass(frozen=True)
class CertificateFacts:
    subject: str
    not_after: datetime
    sha256: str


@dataclass(frozen=True)
class ServiceProvider:
    entity_id: str
    acs_url: str


def read_idp_metadata(data: bytes, *, now: datetime) -> IdpMetadata:
    try:
        root = parse_xml(data)
    except UnsafeXml as error:
        raise Invalid(f"the metadata is not accepted: {error}") from error
    entity = _idp_entity(root)
    for holder in {root, entity}:
        _check_valid_until(holder, now)
    descriptor = entity.find(tag(MD, "IDPSSODescriptor"))
    if descriptor is None or SAMLP not in (descriptor.get("protocolSupportEnumeration") or "").split():
        raise Invalid("the metadata does not describe a SAML 2.0 identity provider")
    return IdpMetadata(
        checked_entity_id(entity.get("entityID") or ""),
        _redirect_sso_url(descriptor),
        _signing_certificates(descriptor),
    )


def checked_entity_id(value: str) -> str:
    entity_id = value.strip()
    if not entity_id or len(entity_id) > SPEC_ENTITY_ID_LENGTH or CONTROL.search(entity_id):
        raise Invalid("the identity provider's entity ID is missing or not usable")
    return entity_id


def checked_sso_url(value: str) -> str:
    address = value.strip()
    parts = urlsplit(address)
    usable = parts.scheme == SECURE_SCHEME and parts.hostname and not CONTROL.search(address)
    if not usable or parts.username or parts.password or parts.fragment:
        raise Invalid("the identity provider's sign-in address must be an https address")
    return address


def normal_certificate(text: str) -> str:
    compact = "".join(PEM_LINE.sub("", text).split())
    try:
        load_certificate(compact)
    except ValueError as error:
        raise Invalid("a signing certificate is not a readable X.509 certificate") from error
    return compact


def load_certificate(compact: str) -> x509.Certificate:
    try:
        der = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("the certificate is not base64") from error
    return x509.load_der_x509_certificate(der)


def certificate_facts(compact: str) -> CertificateFacts:
    certificate = load_certificate(compact)
    try:
        subject = certificate.subject.rfc4514_string()
    except ValueError:
        subject = ""
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    return CertificateFacts(subject, certificate.not_valid_after_utc, fingerprint)


def sp_metadata_xml(sp: ServiceProvider) -> bytes:
    root = etree.Element(tag(MD, "EntityDescriptor"), nsmap={"md": MD})
    root.set("entityID", sp.entity_id)
    descriptor = etree.SubElement(root, tag(MD, "SPSSODescriptor"))
    descriptor.set("AuthnRequestsSigned", "false")
    descriptor.set("WantAssertionsSigned", "true")
    descriptor.set("protocolSupportEnumeration", SAMLP)
    name_format = etree.SubElement(descriptor, tag(MD, "NameIDFormat"))
    name_format.text = EMAIL_FORMAT
    service = etree.SubElement(descriptor, tag(MD, "AssertionConsumerService"))
    service.set("Binding", POST_BINDING)
    service.set("Location", sp.acs_url)
    service.set("index", "0")
    service.set("isDefault", "true")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def _idp_entity(root: etree._Element) -> etree._Element:
    if root.tag == tag(MD, "EntityDescriptor"):
        candidates = [root]
    elif root.tag == tag(MD, "EntitiesDescriptor"):
        candidates = list(root.iter(tag(MD, "EntityDescriptor")))
    else:
        raise Invalid(NOT_METADATA)
    providers = [entity for entity in candidates if entity.find(tag(MD, "IDPSSODescriptor")) is not None]
    if len(providers) != 1:
        raise Invalid("the metadata must describe exactly one identity provider")
    return providers[0]


def _check_valid_until(element: etree._Element, now: datetime) -> None:
    value = element.get("validUntil")
    if not value:
        return
    try:
        until = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise Invalid("the metadata holds a validUntil time it cannot read") from error
    until = until.replace(tzinfo=UTC) if until.tzinfo is None else until.astimezone(UTC)
    if until <= now:
        raise Invalid(f"the metadata expired on {until.date().isoformat()}")


def _redirect_sso_url(descriptor: etree._Element) -> str:
    for service in descriptor.findall(tag(MD, "SingleSignOnService")):
        if service.get("Binding") == REDIRECT_BINDING:
            return checked_sso_url(service.get("Location") or "")
    raise Invalid("the identity provider offers no HTTP-Redirect sign-in address")


def _signing_certificates(descriptor: etree._Element) -> tuple[str, ...]:
    found: list[str] = []
    for key in descriptor.findall(tag(MD, "KeyDescriptor")):
        if key.get("use") not in SIGNING_USES:
            continue
        path = f"{tag(DS, 'KeyInfo')}/{tag(DS, 'X509Data')}/{tag(DS, 'X509Certificate')}"
        for element in key.findall(path):
            compact = normal_certificate(text_of(element))
            if compact not in found:
                found.append(compact)
    if not found:
        raise Invalid("the metadata holds no signing certificate")
    if len(found) > MAX_CERTIFICATES:
        raise Invalid(f"the metadata holds more than {MAX_CERTIFICATES} signing certificates")
    return tuple(found)
