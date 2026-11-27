from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings, site_host
from app.models import HQ_REALM, PRACTICE_REALM, REALMS

__all__ = [
    "CurrentSite",
    "Site",
    "account_space",
    "from_trusted_proxy",
    "public_host",
    "realm_url",
    "request_site",
    "site_for",
]

ANY_PROXY = "*"
FORWARDED_HOST = "x-forwarded-host"
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(frozen=True)
class Site:
    url: str
    realms: tuple[str, ...]

    @property
    def takes_signups(self) -> bool:
        return PRACTICE_REALM in self.realms


def site_for(host: str, settings: Settings) -> Site:
    if not settings.admin_url:
        return Site(settings.app_url, REALMS)
    if host == site_host(settings.admin_url):
        return Site(settings.admin_url, (HQ_REALM,))
    return Site(settings.app_url, (PRACTICE_REALM,))


def public_host(request: Request, settings: Settings) -> str:
    host = request.headers.get("host", "").strip().lower()
    known = {site_host(address) for address in (settings.app_url, settings.admin_url) if address}
    if host in known or not from_trusted_proxy(request, settings.forwarded_allow_ips):
        return host
    forwarded = request.headers.get(FORWARDED_HOST, "").split(",")[0].strip().lower()
    return forwarded or host


def request_site(request: Request) -> Site:
    settings = get_settings()
    return site_for(public_host(request, settings), settings)


CurrentSite = Annotated[Site, Depends(request_site)]


def realm_url(realm: str) -> str:
    settings = get_settings()
    return settings.admin_url if realm == HQ_REALM and settings.admin_url else settings.app_url


def account_space(realm: str) -> tuple[str, ...]:
    return (realm,) if get_settings().admin_url else REALMS


def from_trusted_proxy(request: Request, allowed: str) -> bool:
    peer = request.client.host if request.client else ""
    entries = {entry.strip() for entry in allowed.split(",") if entry.strip()}
    if ANY_PROXY in entries or (peer and peer in entries):
        return True
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(address in network for network in _networks(entries))


def _networks(entries: Iterable[str]) -> list[Network]:
    networks: list[Network] = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue
    return networks
