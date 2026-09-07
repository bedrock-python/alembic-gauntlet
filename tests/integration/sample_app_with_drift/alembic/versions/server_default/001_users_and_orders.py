"""Create users and orders; is_active defaults to false where the model says true.

Revision ID: 0001
Revises:
Create Date: 2026-09-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None

order_status = sa.Enum("new", "paid", "shipped", name="order_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("chk_orders_amount_positive")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_orders_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
    )


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("users")
    order_status.drop(op.get_bind())
