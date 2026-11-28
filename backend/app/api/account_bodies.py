from __future__ import annotations

from typing import Literal

from app.api.bodies import Body
from app.models import MOTION_CHOICES, TEXT_SIZES, THEMES

__all__ = ["AppearanceBody", "PreferencesBody"]


class PreferencesBody(Body):
    notify_digest: bool


class AppearanceBody(Body):
    theme: Literal[THEMES]
    text_size: Literal[TEXT_SIZES]
    reduce_motion: Literal[MOTION_CHOICES]
