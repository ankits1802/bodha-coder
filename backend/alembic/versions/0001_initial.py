from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = Path(__file__).with_name("0001_initial.sql")
PLACES = (
    ("11", "Office"),
    ("12", "Home"),
    ("13", "Assisted living facility"),
    ("02", "Telehealth, other than home"),
    ("10", "Telehealth, in patient's home"),
    ("21", "Inpatient hospital"),
    ("22", "Outpatient hospital, on campus"),
    ("23", "Emergency room"),
    ("31", "Skilled nursing facility"),
    ("32", "Nursing facility"),
)
TABLES = (
    "access_log",
    "activity",
    "demo_requests",
    "decisions",
    "suggestions",
    "code_sets",
    "note_texts",
    "addendum_requests",
    "analyses",
    "notes",
    "batches",
    "mips_lists",
    "providers",
    "places_of_service",
    "sessions",
    "user_tokens",
    "users",
    "practices",
)


def upgrade() -> None:
    for statement in SCHEMA.read_text(encoding="utf-8").split(";\n"):
        if statement.strip():
            op.execute(statement)
    places = sa.table("places_of_service", sa.column("code"), sa.column("name"), sa.column("active"))
    op.bulk_insert(places, [{"code": code, "name": name, "active": True} for code, name in PLACES])


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
