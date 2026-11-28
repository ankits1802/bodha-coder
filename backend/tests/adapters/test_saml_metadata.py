import base64
import zlib
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from lxml import etree

from app.adapters.saml_metadata import (
    ServiceProvider,
    certificate_facts,
    normal_certificate,
    read_idp_metadata,
    sp_metadata_xml,
)
from app.adapters.saml_request import authn_request, redirect_url
from app.core.errors import Invalid
from tests.saml_idp import IDP_ENTITY, IDP_SSO_URL, MD, POST, SAML, SAMLP, idp_metadata

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)
SP = ServiceProvider("https://app.test/api/auth/saml/c-1/metadata", "https://app.test/api/auth/saml/c-1/acs")


def refused(document: bytes) -> str:
    with pytest.raises(Invalid) as caught:
        read_idp_metadata(document, now=NOW)
    return caught.value.message


def test_metadata_gives_the_entity_the_redirect_address_and_every_signing_certificate(idp, next_idp):
    parsed = read_idp_metadata(idp_metadata((idp, next_idp, idp)), now=NOW)
    assert (parsed.entity_id, parsed.sso_url) == (IDP_ENTITY, IDP_SSO_URL)
    assert parsed.certificates == (idp.compact, next_idp.compact)


def test_metadata_without_a_redirect_binding_or_https_or_a_certificate_is_refused(idp):
    assert (
        refused(idp_metadata((idp,), bindings=(POST,)))
        == "the identity provider offers no HTTP-Redirect sign-in address"
    )
    plain = refused(idp_metadata((idp,), sso_url="http://idp.lakeside.example.com/sso"))
    assert plain == "the identity provider's sign-in address must be an https address"
    assert refused(idp_metadata(())) == "the metadata holds no signing certificate"


def test_metadata_with_a_document_type_or_of_another_kind_is_refused(idp):
    declared = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'
    assert refused(declared).startswith("the metadata is not accepted")
    assert refused(b"<html><body>sign in</body></html>") == "the file is not SAML metadata"


def test_expired_metadata_and_metadata_naming_two_providers_are_refused(idp):
    root = etree.fromstring(idp_metadata((idp,)))
    root.set("validUntil", (NOW - timedelta(days=1)).isoformat())
    assert refused(etree.tostring(root)) == "the metadata expired on 2026-11-27"
    group = etree.Element(f"{{{MD}}}EntitiesDescriptor", nsmap={"md": MD})
    group.append(etree.fromstring(idp_metadata((idp,))))
    group.append(etree.fromstring(idp_metadata((idp,), entity_id="https://idp.other.test")))
    assert refused(etree.tostring(group)) == "the metadata must describe exactly one identity provider"


def test_a_pem_certificate_is_stored_as_its_base64_and_described(idp):
    assert normal_certificate(idp.pem) == idp.compact
    facts = certificate_facts(idp.compact)
    assert facts.sha256 == idp.sha256
    assert facts.subject == "CN=idp.lakeside.example.com"
    assert facts.not_after == idp.certificate.not_valid_after_utc
    with pytest.raises(Invalid):
        normal_certificate("not a certificate")


def test_the_service_metadata_names_the_entity_the_acs_and_the_email_format():
    root = etree.fromstring(sp_metadata_xml(SP))
    namespaces = {"md": MD}
    assert root.get("entityID") == SP.entity_id
    descriptor = root.find("md:SPSSODescriptor", namespaces=namespaces)
    assert (descriptor.get("AuthnRequestsSigned"), descriptor.get("WantAssertionsSigned")) == ("false", "true")
    service = descriptor.find("md:AssertionConsumerService", namespaces=namespaces)
    assert (service.get("Binding"), service.get("Location")) == (POST, SP.acs_url)
    name_format = descriptor.find("md:NameIDFormat", namespaces=namespaces).text
    assert name_format == "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


def test_the_request_is_deflated_into_the_redirect_and_keeps_the_provider_query():
    xml = authn_request(SP, request_id="_req-1", destination=IDP_SSO_URL, issued_at=NOW)
    address = redirect_url(IDP_SSO_URL, xml, relay_state="relay-1")
    parts = urlsplit(address)
    query = parse_qs(parts.query)
    assert (parts.netloc, query["tenant"], query["RelayState"]) == (
        "idp.lakeside.example.com",
        ["lakeside"],
        ["relay-1"],
    )
    request = etree.fromstring(zlib.decompress(base64.b64decode(query["SAMLRequest"][0]), -15))
    assert request.tag == f"{{{SAMLP}}}AuthnRequest"
    assert (request.get("ID"), request.get("IssueInstant"), request.get("Destination")) == (
        "_req-1",
        "2026-11-28T12:00:00Z",
        IDP_SSO_URL,
    )
    assert (request.get("AssertionConsumerServiceURL"), request.get("ProtocolBinding")) == (SP.acs_url, POST)
    assert request.find(f"{{{SAML}}}Issuer").text == SP.entity_id
    plain = redirect_url("https://idp.test/sso", xml, relay_state="r")
    assert plain.startswith("https://idp.test/sso?SAMLRequest=")
