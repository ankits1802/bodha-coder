import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(8), nullable=False),
        sa.Column("customer_id", sa.String(255), nullable=True),
        sa.Column("subscription_id", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("interval", sa.String(8), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("past_due_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("provider IN ('stripe', 'paypal')", name=op.f("ck_subscriptions_provider_allowed")),
        sa.CheckConstraint("interval IN ('monthly', 'annual')", name=op.f("ck_subscriptions_interval_allowed")),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'past_due', 'canceled', 'expired')",
            name=op.f("ck_subscriptions_status_allowed"),
        ),
        sa.CheckConstraint("quantity >= 1", name=op.f("ck_subscriptions_quantity_min")),
        sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], name=op.f("fk_subscriptions_practice_id_practices")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint("practice_id", name=op.f("uq_subscriptions_practice_id")),
        sa.UniqueConstraint("provider", "subscription_id", name=op.f("uq_subscriptions_provider")),
    )
    op.create_table(
        "billing_events",
        sa.Column("provider", sa.String(8), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("provider IN ('stripe', 'paypal')", name=op.f("ck_billing_events_provider_allowed")),
        sa.PrimaryKeyConstraint("provider", "event_id", name=op.f("pk_billing_events")),
    )
    op.execute("UPDATE practices SET plan = 'essentials' WHERE plan = 'basic'")


def downgrade() -> None:
    op.execute("UPDATE practices SET plan = 'basic' WHERE plan = 'essentials'")
    op.drop_table("billing_events")
    op.drop_table("subscriptions")
