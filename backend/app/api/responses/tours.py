from typing import Literal

from app.api.responses.base import View
from app.models import TOURS

__all__ = ["Tour", "TourRecord"]

Tour = Literal[TOURS]


class TourRecord(View):
    tour: Tour
    version: int
    completed_at: str | None
    skipped_at: str | None
