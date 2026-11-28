from __future__ import annotations

import httpx
import pytest

from app.adapters.guarded_http import (
    HttpLimits,
    OutboundHttp,
    Redirected,
    RemoteRateLimited,
    TimedOut,
    TooLarge,
    UnsafeAddress,
    is_public_address,
    retry_after_seconds,
)
from tests.ehr_fakes import Sleeps, public_resolver, resolving_to

URL = "https://ehr.example.com/fhir/r4/metadata"
NO_SPACING = HttpLimits(spacing_seconds=0.0)


def _outbound(handler, *, resolver=public_resolver, sleeps: Sleeps | None = None, limits=NO_SPACING) -> OutboundHttp:
    return OutboundHttp(httpx.MockTransport(handler), resolver, sleeps or Sleeps(), limits)


async def _get(outbound: OutboundHttp, url: str = URL, *, max_bytes: int = 1000):
    async with outbound.connect() as http:
        return await http.get(url, headers={"Accept": "application/fhir+json"}, max_bytes=max_bytes)


def _never(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"{request.url} must not be requested")


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "127.0.0.1",
        "169.254.169.254",
        "169.254.170.2",
        "100.64.0.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "::ffff:169.254.169.254",
        "224.0.0.1",
        "0.0.0.0",
    ],
)
def test_private_loopback_link_local_and_mapped_addresses_are_not_public(address):
    assert is_public_address(address) is False


def test_an_ordinary_internet_address_is_public():
    assert is_public_address("93.184.216.34") is True
    assert is_public_address("2606:2800:220:1:248:1893:25c8:1946") is True


@pytest.mark.parametrize(
    "url",
    [
        "http://ehr.example.com/fhir",
        "https://user:secret@ehr.example.com/fhir",
        "ftp://ehr.example.com",
        "https:///fhir",
    ],
)
async def test_only_https_without_credentials_is_fetched(url):
    with pytest.raises(UnsafeAddress):
        await _get(_outbound(_never), url)


async def test_a_name_that_resolves_to_the_metadata_address_is_refused_before_any_request():
    with pytest.raises(UnsafeAddress):
        await _get(_outbound(_never, resolver=resolving_to("169.254.169.254")))


async def test_a_private_address_literal_is_refused():
    with pytest.raises(UnsafeAddress):
        await _get(_outbound(_never), "https://10.1.2.3/fhir/metadata")


async def test_a_busy_server_is_retried_after_the_seconds_it_asks_for():
    answers = [httpx.Response(503, headers={"retry-after": "2"}), httpx.Response(200, content=b"{}")]
    sleeps = Sleeps()

    answer = await _get(_outbound(lambda request: answers.pop(0), sleeps=sleeps))

    assert answer.status == 200
    assert sleeps.waits == [2.0]


async def test_a_server_asking_for_a_longer_pause_than_bodha_waits_stops_the_request():
    sleeps = Sleeps()
    with pytest.raises(RemoteRateLimited):
        await _get(_outbound(lambda request: httpx.Response(429, headers={"retry-after": "600"}), sleeps=sleeps))
    assert sleeps.waits == []


async def test_timeouts_back_off_one_then_two_seconds_and_then_give_up():
    sleeps = Sleeps()

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(TimedOut):
        await _get(_outbound(slow, sleeps=sleeps))
    assert sleeps.waits == [1.0, 2.0]


async def test_a_redirect_on_the_same_host_is_followed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadata"):
            return httpx.Response(302, headers={"location": "/fhir/r4/metadata-v2"})
        return httpx.Response(200, content=b"moved")

    answer = await _get(_outbound(handler))

    assert (answer.status, answer.body, answer.url) == (200, b"moved", "https://ehr.example.com/fhir/r4/metadata-v2")


async def test_a_redirect_to_another_host_is_refused_and_never_requested():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        return httpx.Response(302, headers={"location": "https://storage.elsewhere.example.net/blob"})

    with pytest.raises(Redirected):
        await _get(_outbound(handler))
    assert seen == ["ehr.example.com"]


async def test_an_answer_larger_than_the_limit_is_refused_whether_declared_or_streamed():
    declared = _outbound(lambda request: httpx.Response(200, headers={"content-length": "5000"}, content=b"x" * 5000))
    with pytest.raises(TooLarge):
        await _get(declared)

    async def chunks():
        for _ in range(20):
            yield b"x" * 100

    streamed = _outbound(lambda request: httpx.Response(200, content=chunks()))
    with pytest.raises(TooLarge):
        await _get(streamed)


async def test_requests_to_one_ehr_are_spaced_apart():
    sleeps = Sleeps()
    outbound = _outbound(lambda request: httpx.Response(200), sleeps=sleeps, limits=HttpLimits(spacing_seconds=0.5))
    async with outbound.connect() as http:
        http.clock = lambda: 100.0
        await http.get(URL, headers={}, max_bytes=10)
        await http.get(URL, headers={}, max_bytes=10)
    assert sleeps.waits == [0.5]


def test_retry_after_reads_seconds_and_http_dates():
    assert retry_after_seconds("7") == 7.0
    assert retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0
    assert retry_after_seconds("soon") is None
    assert retry_after_seconds(None) is None
