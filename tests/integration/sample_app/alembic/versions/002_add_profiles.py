"""Add profiles table.

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-01-01 00:01:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a1"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bio", sa.String(1000), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="profiles_user_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="profiles_pkey"),
    )
    op.create_index("idx_profiles_user_id", "profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")
