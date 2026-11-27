from __future__ import annotations

from typing import Literal

from pydantic import EmailStr, Field

from app.api.bodies import Body
from app.core.roles import PRACTICE_ROLES
from app.models import DOMAIN_LENGTH, JOIN_MODES
from app.services.email_domains import ADMIN_MAILBOXES
from app.services.plans import PLAN_KEYS

__all__ = [
    "AccessBody",
    "AttachPracticeBody",
    "CombinedBillingBody",
    "DomainBody",
    "DomainEmailBody",
    "DomainJoinBody",
    "DomainLinkBody",
    "IdentityJoinBody",
    "JoinApprovalBody",
    "JoinChoiceBody",
    "JoinTicketBody",
    "LocationBody",
    "OrganizationAdminBody",
    "OrganizationBody",
    "OrganizationPersonBody",
    "OrganizationUpdateBody",
    "PlacementBody",
]

PracticeRoleName = Literal[PRACTICE_ROLES]
TOKEN_LENGTH = 2000


class OrganizationBody(Body):
    name: str = Field(min_length=2, max_length=200)
    plan: Literal[PLAN_KEYS] = "trial"


class OrganizationUpdateBody(Body):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    plan: Literal[PLAN_KEYS] | None = None


class AttachPracticeBody(Body):
    practice_id: str = Field(min_length=1, max_length=36)


class CombinedBillingBody(Body):
    combined: bool


class OrganizationAdminBody(Body):
    email: EmailStr
    reason: str = Field(min_length=3, max_length=200)


class LocationBody(Body):
    name: str = Field(min_length=2, max_length=200)
    time_zone: str = Field(min_length=1, max_length=64)
    agreed: Literal[True]


class AccessBody(Body):
    role: PracticeRoleName
    reason: str = Field(min_length=3, max_length=200)


class PlacementBody(Body):
    practice_id: str = Field(min_length=1, max_length=36)
    role: PracticeRoleName


class OrganizationPersonBody(Body):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    practices: list[PlacementBody] = Field(min_length=1, max_length=50)


class DomainBody(Body):
    domain: str = Field(min_length=4, max_length=DOMAIN_LENGTH)
    practice_id: str | None = Field(default=None, max_length=36)


class DomainEmailBody(Body):
    mailbox: Literal[ADMIN_MAILBOXES]


class DomainJoinBody(Body):
    mode: Literal[JOIN_MODES]
    role: PracticeRoleName = "viewer"


class DomainLinkBody(Body):
    token: str = Field(min_length=16, max_length=200)


class JoinApprovalBody(Body):
    role: PracticeRoleName


class JoinTicketBody(Body):
    token: str = Field(min_length=16, max_length=TOKEN_LENGTH)


class JoinChoiceBody(JoinTicketBody):
    join: bool


class IdentityJoinBody(Body):
    name: str = Field(min_length=1, max_length=120)
