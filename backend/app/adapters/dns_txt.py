from __future__ import annotations

import logging
from typing import Protocol

import dns.asyncresolver
import dns.exception
import dns.resolver

from app.core.errors import Unavailable

__all__ = ["DnsTxtResolver", "DnsUnavailable", "TxtResolver"]

logger = logging.getLogger("bodha.dns")
LOOKUP_SECONDS = 5.0
TXT = "TXT"


class DnsUnavailable(Unavailable):
    def __init__(self) -> None:
        super().__init__("the domain's DNS records could not be read; try again")


class TxtResolver(Protocol):
    async def txt_records(self, domain: str) -> list[str]: ...


class DnsTxtResolver:
    def __init__(self, *, lifetime_seconds: float = LOOKUP_SECONDS) -> None:
        self._lifetime = lifetime_seconds

    async def txt_records(self, domain: str) -> list[str]:
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.lifetime = self._lifetime
            answer = await resolver.resolve(domain, TXT)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return []
        except dns.exception.DNSException as error:
            logger.warning("DNS TXT lookup failed (%s)", type(error).__name__)
            raise DnsUnavailable() from error
        return [b"".join(record.strings).decode("utf-8", errors="replace") for record in answer]
