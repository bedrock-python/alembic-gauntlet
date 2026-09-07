"""Unit tests for the schema diff helpers."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Boolean, CheckConstraint, Column, Enum, Integer, MetaData, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql.base import PGInspector

from alembic_gauntlet.utils.diff import (
    DEFAULT_IGNORE_TABLES,
    compare_check_constraints,
    compare_enums,
    is_ignored_diff_item,
)

_CONN = MagicMock(dialect=postgresql.dialect())
_CK_CONVENTION = {"ck": "chk_%(table_name)s_%(constraint_name)s"}
_ORDER_STATUS = {"name": "order_status", "schema": "s", "visible": True, "labels": ["new", "paid", "shipped"]}


def _make_table(name: str) -> MagicMock:
    """Create a mock table with the given name."""
    table = MagicMock()
    table.name = name
    return table


def _make_index_on_table(table_name: str) -> MagicMock:
    """Create a mock index on a table with the given name."""
    table = _make_table(table_name)
    index = MagicMock()
    index.table = table
    return index


@pytest.mark.unit
@pytest.mark.parametrize(
    ("operation", "subject_factory", "table_name"),
    [
        ("remove_table", _make_table, "alembic_version"),
        ("remove_index", _make_index_on_table, "alembic_version"),
        ("remove_table", _make_table, "events_default"),
    ],
    ids=["remove_alembic_version_table", "remove_index_on_alembic_version", "remove_custom_ignored_table"],
)
def test__is_ignored_diff_item__ignored_operation__returns_true(
    operation: str, subject_factory: callable, table_name: str
) -> None:
    # Arrange
    ignore_set = DEFAULT_IGNORE_TABLES | frozenset({"events_default"})
    subject = subject_factory(table_name)
    diff_item = (operation, subject)

    # Act
    result = is_ignored_diff_item(diff_item, ignore_set)

    # Assert
    assert result is True


@pytest.mark.unit
@pytest.mark.parametrize(
    ("operation", "subject_factory", "table_name"),
    [
        ("remove_table", _make_table, "users"),
        ("remove_index", _make_index_on_table, "users"),
        ("add_column", lambda _: MagicMock(), None),
    ],
    ids=["remove_normal_table", "remove_index_on_normal_table", "add_column_operation"],
)
def test__is_ignored_diff_item__not_ignored_operation__returns_false(
    operation: str, subject_factory: callable, table_name: str | None
) -> None:
    # Arrange
    subject = subject_factory(table_name) if table_name else subject_factory(None)
    diff_item = (operation, subject)

    # Act
    result = is_ignored_diff_item(diff_item, DEFAULT_IGNORE_TABLES)

    # Assert
    assert result is False


@pytest.mark.unit
def test__is_ignored_diff_item__single_element_tuple__returns_false() -> None:
    # Arrange
    diff_item = ("remove_table",)

    # Act
    result = is_ignored_diff_item(diff_item, DEFAULT_IGNORE_TABLES)

    # Assert
    assert result is False


@pytest.mark.unit
def test__is_ignored_diff_item__table_name_none__returns_false() -> None:
    # Arrange
    table = _make_table(None)
    diff_item = ("remove_table", table)

    # Act
    result = is_ignored_diff_item(diff_item, DEFAULT_IGNORE_TABLES)

    # Assert
    assert result is False


@pytest.fixture
def inspector() -> Iterator[MagicMock]:
    """A PostgreSQL inspector with no constraints and no enums, patched into the module."""
    mock = MagicMock(spec=PGInspector)
    mock.get_check_constraints.return_value = []
    mock.get_enums.return_value = []
    with patch("alembic_gauntlet.utils.diff.inspect", return_value=mock):
        yield mock


def _orders(metadata: MetaData, *constraints: CheckConstraint, status: Enum | None = None) -> Table:
    columns = [Column("id", Integer, primary_key=True), Column("amount", Integer)]
    if status is not None:
        columns.append(Column("status", status))
    return Table("orders", metadata, *columns, *constraints)


@pytest.mark.unit
def test__compare_check_constraints__missing_in_database__reported(inspector: MagicMock) -> None:
    metadata = MetaData(naming_convention=_CK_CONVENTION)
    _orders(metadata, CheckConstraint("amount > 0", name="amount_positive"))

    differences = compare_check_constraints(_CONN, metadata, "s")

    assert differences == [
        "Check constraint 'chk_orders_amount_positive' on table 'orders' is in the models but not in the database."
    ]
    inspector.get_check_constraints.assert_called_once_with("orders", schema="s")


@pytest.mark.unit
def test__compare_check_constraints__in_sync__empty(inspector: MagicMock) -> None:
    metadata = MetaData(naming_convention=_CK_CONVENTION)
    _orders(metadata, CheckConstraint("amount > 0", name="amount_positive"))
    inspector.get_check_constraints.return_value = [{"name": "chk_orders_amount_positive", "sqltext": "amount > 0"}]

    assert compare_check_constraints(_CONN, metadata, "s") == []


@pytest.mark.unit
def test__compare_check_constraints__unexpected_in_database__reported(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata)
    inspector.get_check_constraints.return_value = [{"name": "chk_orders_stale", "sqltext": "amount < 100"}]

    assert compare_check_constraints(_CONN, metadata, "s") == [
        "Check constraint 'chk_orders_stale' on table 'orders' is in the database but not in the models."
    ]


@pytest.mark.unit
def test__compare_check_constraints__unnamed_in_models__nothing_reported(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, CheckConstraint("amount > 0"))
    inspector.get_check_constraints.return_value = [{"name": "orders_amount_check", "sqltext": "amount > 0"}]

    assert compare_check_constraints(_CONN, metadata, "s") == []


@pytest.mark.unit
def test__compare_check_constraints__deferred_name__resolved_through_convention(inspector: MagicMock) -> None:
    metadata = MetaData(naming_convention={"ck": "ck_%(table_name)s_%(column_0_name)s"})
    Table("users", metadata, Column("id", Integer, primary_key=True), Column("active", Boolean(create_constraint=True)))

    assert compare_check_constraints(_CONN, metadata, "s") == [
        "Check constraint 'ck_users_active' on table 'users' is in the models but not in the database."
    ]


@pytest.mark.unit
def test__compare_check_constraints__ignored_table__skipped(inspector: MagicMock) -> None:
    metadata = MetaData(naming_convention=_CK_CONVENTION)
    _orders(metadata, CheckConstraint("amount > 0", name="amount_positive"))

    assert compare_check_constraints(_CONN, metadata, "s", frozenset({"orders"})) == []
    inspector.get_check_constraints.assert_not_called()


@pytest.mark.unit
def test__compare_enums__in_sync__empty(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", "shipped", name="order_status"))
    inspector.get_enums.return_value = [_ORDER_STATUS]

    assert compare_enums(_CONN, metadata, "s") == []
    inspector.get_enums.assert_called_once_with(schema="*")


@pytest.mark.unit
@pytest.mark.parametrize(
    "labels",
    [["new", "paid"], ["new", "shipped", "paid"], ["new", "paid", "shipped", "refunded"]],
    ids=["missing_value", "different_order", "extra_value"],
)
def test__compare_enums__values_differ__reported(inspector: MagicMock, labels: list[str]) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", "shipped", name="order_status"))
    inspector.get_enums.return_value = [{**_ORDER_STATUS, "labels": labels}]

    assert compare_enums(_CONN, metadata, "s") == [
        f"Enum type 'order_status' has values {labels} in the database and ['new', 'paid', 'shipped'] in the models."
    ]


@pytest.mark.unit
def test__compare_enums__type_missing__reported(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", name="order_status"))

    assert compare_enums(_CONN, metadata, "s") == [
        "Enum type 'order_status' in schema 's' is in the models but not in the database."
    ]


@pytest.mark.unit
def test__compare_enums__explicit_schema__looked_up_there(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", "shipped", name="order_status", schema="types"))
    inspector.get_enums.return_value = [{**_ORDER_STATUS, "schema": "types"}]

    assert compare_enums(_CONN, metadata, "s") == []


@pytest.mark.unit
def test__compare_enums__non_native_enum__skipped(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", name="order_status", native_enum=False))

    assert compare_enums(_CONN, metadata, "s") == []


@pytest.mark.unit
def test__compare_enums__ignored_table__skipped(inspector: MagicMock) -> None:
    metadata = MetaData()
    _orders(metadata, status=Enum("new", "paid", name="order_status"))

    assert compare_enums(_CONN, metadata, "s", frozenset({"orders"})) == []
