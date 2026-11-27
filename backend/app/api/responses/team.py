from typing import Literal

from app.api.responses.base import Role, View

__all__ = ["MemberStatus", "TeamList", "TeamMember"]

MemberStatus = Literal["invited", "active", "blocked"]


class TeamMember(View):
    id: str
    name: str
    email: str
    role: Role
    status: MemberStatus
    mfa_enabled: bool
    last_active_at: str | None


class TeamList(View):
    seats: int
    members: list[TeamMember]
