import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

REALM_OF_ROLE = "CASE WHEN role = 'hq' THEN 'hq' ELSE 'practice' END"
EMAIL_UNIQUE = op.f("uq_users_email")
USER_REALM_UNIQUE = op.f("uq_users_id")
IDENTITY_USER = op.f("fk_user_identities_user_id_users")
IDENTITY_SUBJECT_UNIQUE = op.f("uq_user_identities_provider")
SHARED_ACROSS_REALMS = (
    "SELECT (SELECT count(*) FROM (SELECT email FROM users GROUP BY email HAVING count(*) > 1) AS emails)"
    " + (SELECT count(*) FROM (SELECT provider, subject FROM user_identities"
    " GROUP BY provider, subject HAVING count(*) > 1) AS identities)"
)


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("realm", sa.String(16), sa.Computed(REALM_OF_ROLE, persisted=True), nullable=False)
    )
    op.drop_constraint(EMAIL_UNIQUE, "users", type_="unique")
    op.create_unique_constraint(EMAIL_UNIQUE, "users", ["email", "realm"])
    op.create_unique_constraint(USER_REALM_UNIQUE, "users", ["id", "realm"])
    op.add_column("user_identities", sa.Column("realm", sa.String(16), nullable=True))
    op.execute("UPDATE user_identities SET realm = users.realm FROM users WHERE users.id = user_identities.user_id")
    op.alter_column("user_identities", "realm", nullable=False, server_default=sa.text("'practice'"))
    op.drop_constraint(IDENTITY_USER, "user_identities", type_="foreignkey")
    op.create_foreign_key(IDENTITY_USER, "user_identities", "users", ["user_id", "realm"], ["id", "realm"])
    op.drop_constraint(IDENTITY_SUBJECT_UNIQUE, "user_identities", type_="unique")
    op.create_unique_constraint(IDENTITY_SUBJECT_UNIQUE, "user_identities", ["provider", "subject", "realm"])


def downgrade() -> None:
    shared = op.get_bind().scalar(sa.text(SHARED_ACROSS_REALMS))
    if shared:
        raise RuntimeError(f"{shared} emails or sign-in identities belong to both an HQ and a practice account")
    op.drop_constraint(IDENTITY_SUBJECT_UNIQUE, "user_identities", type_="unique")
    op.create_unique_constraint(IDENTITY_SUBJECT_UNIQUE, "user_identities", ["provider", "subject"])
    op.drop_constraint(IDENTITY_USER, "user_identities", type_="foreignkey")
    op.create_foreign_key(IDENTITY_USER, "user_identities", "users", ["user_id"], ["id"])
    op.drop_column("user_identities", "realm")
    op.drop_constraint(USER_REALM_UNIQUE, "users", type_="unique")
    op.drop_constraint(EMAIL_UNIQUE, "users", type_="unique")
    op.create_unique_constraint(EMAIL_UNIQUE, "users", ["email"])
    op.drop_column("users", "realm")
