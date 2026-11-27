from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, one_of, timestamp, utcnow

BILLING_PROVIDERS = ("stripe", "paypal")
BILLING_INTERVALS = ("monthly", "annual")
SUBSCRIPTION_STATUSES = ("pending", "active", "past_due", "canceled", "expired")


class Subscription(IdMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("provider", "subscription_id"),
        one_of("provider", BILLING_PROVIDERS),
        one_of("interval", BILLING_INTERVALS),
        one_of("status", SUBSCRIPTION_STATUSES),
        CheckConstraint("quantity >= 1", name="quantity_min"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(8))
    customer_id: Mapped[str | None] = mapped_column(String(255))
    subscription_id: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(16))
    interval: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(12))
    current_period_end: Mapped[datetime | None] = timestamp()
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    past_due_since: Mapped[datetime | None] = timestamp()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BillingEvent(Base):
    __tablename__ = "billing_events"
    __table_args__ = (one_of("provider", BILLING_PROVIDERS),)
    provider: Mapped[str] = mapped_column(String(8), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    kind: Mapped[str] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
