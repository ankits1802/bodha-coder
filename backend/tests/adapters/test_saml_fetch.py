import httpx
import pytest

from app.adapters.saml_fetch import HttpsMetadataSource, metadata_address
from app.adapters.saml_xml import MAX_XML_BYTES
from app.core.errors import Invalid

ADDRESS = "https://idp.lakeside.example.com/metadata.xml"
PUBLIC = ["93.184.215.14"]


def resolving(addresses: list[str]):
    async def resolve(host: str, port: int) -> list[str]:
        return addresses

    return resolve


def source(handler, addresses: list[str] = PUBLIC) -> HttpsMetadataSource:
    return HttpsMetadataSource(resolve=resolving(addresses), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "address",
    [
        "http://idp.lakeside.example.com/metadata.xml",
        "https://10.0.0.5/metadata.xml",
        "https://[::1]/metadata.xml",
        "https://user:secret@idp.lakeside.example.com/metadata.xml",
        "ftp://idp.lakeside.example.com/metadata.xml",
    ],
)
def test_only_https_addresses_with_a_host_name_are_fetched(address):
    with pytest.raises(Invalid):
        metadata_address(address)


def test_an_address_keeps_its_host_and_port():
    assert metadata_address(" https://idp.test:8443/m ") == ("https://idp.test:8443/m", "idp.test", 8443)


@pytest.mark.parametrize("addresses", [["10.1.2.3"], ["169.254.169.254"], ["127.0.0.1"], PUBLIC + ["192.168.0.2"], []])
async def test_a_host_that_resolves_to_a_private_address_is_never_contacted(addresses):
    contacted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        contacted.append(str(request.url))
        return httpx.Response(200, content=b"<x/>")

    with pytest.raises(Invalid) as caught:
        await source(handler, addresses).fetch(ADDRESS)
    assert caught.value.message == "the metadata address must point to a public host"
    assert contacted == []


async def test_the_document_is_read_without_following_redirects():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/metadata.xml":
            return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest"})
        return httpx.Response(200, content=b"<x/>")

    with pytest.raises(Invalid) as caught:
        await source(handler).fetch(ADDRESS)
    assert caught.value.message == "the metadata address answered 302"


async def test_a_public_document_is_returned_and_an_oversized_one_refused():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["accept"])
        body = b"<md/>" if request.url.path == "/metadata.xml" else b"x" * (MAX_XML_BYTES + 1)
        return httpx.Response(200, content=body)

    assert await source(handler).fetch(ADDRESS) == b"<md/>"
    assert seen[0].startswith("application/samlmetadata+xml")
    with pytest.raises(Invalid) as caught:
        await source(handler).fetch("https://idp.lakeside.example.com/huge.xml")
    assert caught.value.message == "the metadata is too large"
