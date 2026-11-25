from __future__ import annotations

from app.core.errors import Unavailable


class MessengerNotConfigured(Unavailable):
    pass


class MessageNotSent(Unavailable):
    pass
