"""enums, users, user_preferences

Revision ID: 001
Revises:
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Every enum from docs/02-datamodel.md, created up front even though most
# tables that use them don't exist until later migrations — keeps the
# vocabulary in one place and every later migration append-only.
UNIT = [
    "g",
    "kg",
    "ml",
    "l",
    "el",
    "tl",
    "stuk",
    "snuf",
    "teentje",
    "bosje",
    "blikje",
    "pakje",
    "plak",
    "handvol",
    "naar_smaak",
]
SHELF_CATEGORY = [
    "groente_fruit",
    "vlees_vis",
    "zuivel_eieren",
    "brood_bakkerij",
    "houdbaar",
    "kruiden_specerijen",
    "diepvries",
    "dranken",
    "overig",
]
PROVENANCE = ["explicit", "derived", "estimated", "missing"]
MEAL_TYPE = ["ontbijt", "lunch", "diner", "tussendoor"]
SOURCE_PLATFORM = ["tiktok", "instagram", "youtube", "pinterest", "web", "photo_ocr", "manual"]
IMPORT_STATUS = [
    "queued",
    "fetching",
    "synthesizing",
    "ready_for_review",
    "saved",
    "failed",
    "cancelled",
]
PLAN_TIER = ["free", "premium"]
GROUP_ROLE = ["owner", "member"]
DIFFICULTY = ["makkelijk", "gemiddeld", "uitdagend"]

ENUMS: list[tuple[str, list[str]]] = [
    ("unit", UNIT),
    ("shelf_category", SHELF_CATEGORY),
    ("provenance", PROVENANCE),
    ("meal_type", MEAL_TYPE),
    ("source_platform", SOURCE_PLATFORM),
    ("import_status", IMPORT_STATUS),
    ("plan_tier", PLAN_TIER),
    ("group_role", GROUP_ROLE),
    ("difficulty", DIFFICULTY),
]


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS:
        sa.Enum(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("clerk_user_id", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("household_size", sa.SmallInteger(), nullable=False, server_default=sa.text("2")),
        sa.Column("locale", sa.Text(), nullable=False, server_default=sa.text("'nl-NL'")),
        sa.Column(
            "tier",
            postgresql.ENUM(*PLAN_TIER, name="plan_tier", create_type=False),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
        sa.Column("trial_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_email", "users", ["email"], postgresql_where=sa.text("deleted_at IS NULL")
    )

    op.create_table(
        "user_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "diets", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "allergens", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "default_servings", sa.SmallInteger(), nullable=False, server_default=sa.text("2")
        ),
        sa.Column(
            "show_original_units", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("fan_oven_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_cooking", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_defrost", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notif_group", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for name, values in reversed(ENUMS):
        sa.Enum(*values, name=name).drop(bind, checkfirst=True)
