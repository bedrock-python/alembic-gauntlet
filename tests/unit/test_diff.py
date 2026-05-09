"""Unit tests for schema diff filtering."""

from unittest.mock import MagicMock

import pytest

from alembic_gauntlet.utils.diff import DEFAULT_IGNORE_TABLES, is_ignored_diff_item


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
