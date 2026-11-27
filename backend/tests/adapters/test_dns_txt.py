import dns.asyncresolver
import dns.exception
import dns.resolver
import pytest

from app.adapters.dns_txt import DnsTxtResolver, DnsUnavailable

DOMAIN = "lakeside.example.com"


class TxtAnswer:
    def __init__(self, *strings: bytes) -> None:
        self.strings = strings


def answering(found):
    async def resolve(self, name, kind):
        assert kind == "TXT"
        if isinstance(found, Exception):
            raise found
        return found[name]

    return resolve


async def test_each_record_joins_its_strings(monkeypatch):
    records = {DOMAIN: [TxtAnswer(b"bodha-verify=", b"abc123"), TxtAnswer(b"v=spf1 -all")]}
    monkeypatch.setattr(dns.asyncresolver.Resolver, "resolve", answering(records))
    assert await DnsTxtResolver().txt_records(DOMAIN) == ["bodha-verify=abc123", "v=spf1 -all"]


@pytest.mark.parametrize("missing", [dns.resolver.NXDOMAIN(), dns.resolver.NoAnswer()])
async def test_a_name_without_records_has_none(monkeypatch, missing):
    monkeypatch.setattr(dns.asyncresolver.Resolver, "resolve", answering(missing))
    assert await DnsTxtResolver().txt_records(DOMAIN) == []


async def test_a_lookup_that_fails_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(dns.asyncresolver.Resolver, "resolve", answering(dns.exception.Timeout()))
    with pytest.raises(DnsUnavailable):
        await DnsTxtResolver().txt_records(DOMAIN)
