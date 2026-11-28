from __future__ import annotations

from collections.abc import Sequence

import cryptography.exceptions
from cryptography import x509
from lxml import etree
from signxml import SignatureConfiguration, VerifyResult, XMLVerifier
from signxml.exceptions import SignXMLException

from app.adapters.saml_xml import SAML, hardened_parser, tag

__all__ = ["ASSERTION_SIGNATURE", "RESPONSE_SIGNATURE", "signed_element"]

RESPONSE_SIGNATURE = "./"
ASSERTION_SIGNATURE = f"./{tag(SAML, 'Assertion')}/"
SAML_ID = "ID"
NOT_VERIFIED = (
    SignXMLException,
    cryptography.exceptions.InvalidSignature,
    cryptography.exceptions.UnsupportedAlgorithm,
    etree.LxmlError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    AssertionError,
)


def signed_element(document: bytes, location: str, certificates: Sequence[x509.Certificate]) -> etree._Element | None:
    config = SignatureConfiguration(location=location, expect_references=1)
    for certificate in certificates:
        try:
            result = XMLVerifier().verify(
                document, x509_cert=certificate, expect_config=config, parser=hardened_parser(), id_attribute=SAML_ID
            )
        except NOT_VERIFIED:
            continue
        if isinstance(result, VerifyResult) and result.signed_xml is not None:
            return result.signed_xml
    return None
