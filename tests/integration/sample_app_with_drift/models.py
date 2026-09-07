"""SQLAlchemy ORM models with a server default, a CHECK constraint and an enum (issue #37)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, MetaData, Numeric, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "idx_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "chk_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class OrderDB(Base):
    """The convention turns ``amount_positive`` into ``chk_orders_amount_positive``."""

    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(Enum("new", "paid", "shipped", name="order_status"), nullable=False)
