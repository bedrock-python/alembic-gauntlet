"""Create users and orders; orders is raw SQL, so PostgreSQL names its primary and foreign keys.

Revision ID: 0001
Revises:
Create Date: 2026-10-16 00:00:00.000000
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
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    order_status.create(op.get_bind())
    # No names on the primary and foreign key: PostgreSQL calls them orders_pkey and orders_user_id_fkey.
    op.execute(
        "CREATE TABLE orders ("
        "id integer PRIMARY KEY, "
        "user_id integer NOT NULL REFERENCES users (id), "
        "amount numeric(12, 2) NOT NULL, "
        "status order_status NOT NULL, "
        "CONSTRAINT chk_orders_amount_positive CHECK (amount > 0))"
    )


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("users")
    order_status.drop(op.get_bind())
