from __future__ import annotations

from lxml import etree

__all__ = [
    "DS",
    "MD",
    "SAML",
    "SAMLP",
    "UnsafeXml",
    "hardened_parser",
    "ids_in",
    "parse_xml",
    "tag",
    "text_of",
]

SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
MD = "urn:oasis:names:tc:SAML:2.0:metadata"
DS = "http://www.w3.org/2000/09/xmldsig#"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ID_ATTRIBUTES = ("ID", "Id", "id", XML_ID)
MAX_XML_BYTES = 1_000_000
DECLARATIONS = (b"<!DOCTYPE", b"<!ENTITY")


class UnsafeXml(ValueError):
    pass


def tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def hardened_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )


def parse_xml(data: bytes) -> etree._Element:
    if len(data) > MAX_XML_BYTES:
        raise UnsafeXml("the document is too large")
    upper = data.upper()
    if any(marker in upper for marker in DECLARATIONS):
        raise UnsafeXml("document type declarations are not accepted")
    try:
        root = etree.fromstring(data, parser=hardened_parser())
    except (etree.XMLSyntaxError, ValueError) as error:
        raise UnsafeXml("the document is not well-formed XML") from error
    docinfo = root.getroottree().docinfo
    if docinfo.internalDTD is not None or docinfo.externalDTD is not None or docinfo.doctype:
        raise UnsafeXml("document type declarations are not accepted")
    if next(root.iter(etree.Entity), None) is not None:
        raise UnsafeXml("entities are not accepted")
    return root


def text_of(element: etree._Element | None) -> str:
    if element is None or len(element) > 0:
        return ""
    return (element.text or "").strip()


def ids_in(root: etree._Element) -> list[str]:
    elements = root.iter(etree.Element)
    return [value for element in elements for name in ID_ATTRIBUTES if (value := element.get(name)) is not None]
