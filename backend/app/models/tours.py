from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, one_of, timestamp
from app.models.tables import REALMS

TOURS = REALMS
TOUR_OUTCOMES = ("completed", "skipped")
TOUR_VERSION_LIMIT = 1000


class PersonTour(Base):
    __tablename__ = "person_tours"
    __table_args__ = (
        one_of("tour", TOURS),
        CheckConstraint("version >= 1", name="version_min"),
        CheckConstraint("(completed_at IS NULL) <> (skipped_at IS NULL)", name="one_outcome"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tour: Mapped[str] = mapped_column(String(16), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    completed_at: Mapped[datetime | None] = timestamp()
    skipped_at: Mapped[datetime | None] = timestamp()
