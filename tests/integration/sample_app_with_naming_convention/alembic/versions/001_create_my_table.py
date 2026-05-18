"""create my_table with unique name column.

Revision ID: 001
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "my_table",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_my_table")),
        sa.UniqueConstraint("name", name=op.f("uq_my_table_name")),
    )


def downgrade() -> None:
    op.drop_table("my_table")
