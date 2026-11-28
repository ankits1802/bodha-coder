from __future__ import annotations

import base64
import secrets
import zlib
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit

from lxml import etree

from app.adapters.saml_metadata import POST_BINDING, ServiceProvider
from app.adapters.saml_xml import SAML, SAMLP, tag

__all__ = ["authn_request", "new_request_id", "redirect_url", "saml_instant"]

REQUEST_ID_BYTES = 20
RAW_DEFLATE = -15


def new_request_id() -> str:
    return "_" + secrets.token_hex(REQUEST_ID_BYTES)


def saml_instant(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def authn_request(sp: ServiceProvider, *, request_id: str, destination: str, issued_at: datetime) -> bytes:
    request = etree.Element(tag(SAMLP, "AuthnRequest"), nsmap={"samlp": SAMLP, "saml": SAML})
    request.set("ID", request_id)
    request.set("Version", "2.0")
    request.set("IssueInstant", saml_instant(issued_at))
    request.set("Destination", destination)
    request.set("AssertionConsumerServiceURL", sp.acs_url)
    request.set("ProtocolBinding", POST_BINDING)
    issuer = etree.SubElement(request, tag(SAML, "Issuer"))
    issuer.text = sp.entity_id
    policy = etree.SubElement(request, tag(SAMLP, "NameIDPolicy"))
    policy.set("AllowCreate", "true")
    return etree.tostring(request)


def redirect_url(sso_url: str, request_xml: bytes, *, relay_state: str) -> str:
    compressor = zlib.compressobj(wbits=RAW_DEFLATE)
    deflated = compressor.compress(request_xml) + compressor.flush()
    encoded = base64.b64encode(deflated).decode("ascii")
    query = urlencode({"SAMLRequest": encoded, "RelayState": relay_state})
    separator = "&" if urlsplit(sso_url).query else "?"
    return f"{sso_url}{separator}{query}"
