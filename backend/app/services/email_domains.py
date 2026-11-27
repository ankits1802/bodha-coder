from __future__ import annotations

import re

from app.core.errors import Invalid

__all__ = [
    "ADMIN_MAILBOXES",
    "PUBLIC_EMAIL_DOMAINS",
    "claimable_domain",
    "domain_of",
    "is_public_domain",
    "normal_domain",
]

ADMIN_MAILBOXES = ("admin", "administrator", "hostmaster", "postmaster", "webmaster")
PUBLIC_EMAIL_DOMAINS = frozenset(
    {
        "126.com",
        "163.com",
        "aim.com",
        "aol.com",
        "att.net",
        "bellsouth.net",
        "btinternet.com",
        "charter.net",
        "comcast.net",
        "cox.net",
        "earthlink.net",
        "email.com",
        "fastmail.com",
        "gmail.com",
        "gmx.com",
        "gmx.de",
        "gmx.net",
        "googlemail.com",
        "hey.com",
        "hotmail.co.uk",
        "hotmail.com",
        "hushmail.com",
        "icloud.com",
        "inbox.com",
        "juno.com",
        "live.com",
        "mac.com",
        "mail.com",
        "mail.ru",
        "me.com",
        "msn.com",
        "naver.com",
        "netzero.net",
        "optonline.net",
        "outlook.com",
        "pm.me",
        "proton.me",
        "protonmail.com",
        "qq.com",
        "rediffmail.com",
        "rocketmail.com",
        "sbcglobal.net",
        "tuta.io",
        "tutanota.com",
        "verizon.net",
        "web.de",
        "yahoo.co.in",
        "yahoo.co.uk",
        "yahoo.com",
        "yandex.com",
        "yandex.ru",
        "ymail.com",
        "zoho.com",
        "zohomail.com",
    }
)
LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
TOP_LABEL = r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])"
DOMAIN_PATTERN = re.compile(rf"^(?=.{{4,253}}$)(?:{LABEL}\.)+{TOP_LABEL}$")
NOT_A_DOMAIN = "enter a domain such as example.com"


def normal_domain(text: str) -> str:
    found = text.strip().lower().removeprefix("@").rstrip(".")
    if not DOMAIN_PATTERN.match(found):
        raise Invalid(NOT_A_DOMAIN)
    return found


def is_public_domain(domain: str) -> bool:
    return any(domain == public or domain.endswith(f".{public}") for public in PUBLIC_EMAIL_DOMAINS)


def claimable_domain(text: str) -> str:
    domain = normal_domain(text)
    if is_public_domain(domain):
        raise Invalid(f"public email services such as {domain} cannot be claimed")
    return domain


def domain_of(email: str) -> str | None:
    _, at, domain = email.strip().lower().rpartition("@")
    return domain.rstrip(".") if at and domain else None
