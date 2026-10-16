"""Add users.is_active; the downgrade forgets to drop it.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 00:00:01.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    pass
