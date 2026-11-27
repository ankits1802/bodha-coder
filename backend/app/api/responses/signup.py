from app.api.responses.auth import IdentityProviderName
from app.api.responses.base import View

__all__ = ["PendingIdentity"]


class PendingIdentity(View):
    email: str
    name: str
    provider: IdentityProviderName
    has_account: bool
