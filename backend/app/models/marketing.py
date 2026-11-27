from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin


class DemoRequest(IdMixin, Base):
    __tablename__ = "demo_requests"
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    organization: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
