"""Schema diff helpers for migration consistency tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic.util.sqla_compat import _get_constraint_final_name
from sqlalchemy import CheckConstraint, Enum, inspect
from sqlalchemy.dialects.postgresql.base import PGInspector

if TYPE_CHECKING:
    from sqlalchemy import MetaData
    from sqlalchemy.engine import Connection

DEFAULT_IGNORE_TABLES: frozenset[str] = frozenset({"alembic_version"})


def is_ignored_diff_item(diff_item: tuple, ignore_tables: frozenset[str]) -> bool:
    """Return ``True`` if this diff item should be excluded from schema diff checks.

    Filters out tables and their indexes that exist in the database but are absent
    from ORM metadata — for example, partition tables auto-created by PostgreSQL.

    Args:
        diff_item: A single item from Alembic's ``compare_metadata()`` result.
        ignore_tables: Set of table names to skip.
    """
    if len(diff_item) < 2:
        return False
    op, first = diff_item[0], diff_item[1]
    if op == "remove_table":
        name = getattr(first, "name", None)
        return name in ignore_tables if name else False
    if op == "remove_index":
        table = getattr(first, "table", None)
        name = getattr(table, "name", None) if table is not None else None
        return name in ignore_tables if name else False
    return False


def compare_check_constraints(
    sync_conn: Connection,
    metadata: MetaData,
    schema: str,
    ignore_tables: frozenset[str] = frozenset(),
) -> list[str]:
    """Compare the CHECK constraints ``metadata`` declares with the ones in ``schema``, by name.

    Alembic's ``compare_metadata()`` never looks at CHECK constraints. Names are resolved
    the way the DDL would render them — the metadata's naming convention applied, a
    deferred name such as ``Boolean(create_constraint=True)`` filled in, anything over 63
    characters truncated — through the same Alembic helper autogenerate uses for index
    and unique constraint names.

    A named constraint the models declare and the database lacks is always reported.
    One the database has and the models do not is reported unless the table also
    declares an unnamed check constraint, which carries whatever name PostgreSQL gave
    it. Unnamed constraints are never compared.

    Args:
        sync_conn: Synchronous SQLAlchemy connection.
        metadata: SQLAlchemy ``MetaData`` of the ORM models.
        schema: PostgreSQL schema the migrations ran in.
        ignore_tables: Table names to skip.

    Returns:
        One line per difference; empty when the constraints match.
    """
    inspector = inspect(sync_conn)
    differences: list[str] = []
    for table in metadata.sorted_tables:
        if table.name in ignore_tables:
            continue
        names = {
            _get_constraint_final_name(constraint, sync_conn.dialect)
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        expected = {name for name in names if name}
        actual = {name for c in inspector.get_check_constraints(table.name, schema=schema) if (name := c["name"])}
        for name in sorted(expected - actual):
            differences.append(
                f"Check constraint '{name}' on table '{table.name}' is in the models but not in the database."
            )
        if None not in names:
            for name in sorted(actual - expected):
                differences.append(
                    f"Check constraint '{name}' on table '{table.name}' is in the database but not in the models."
                )
    return differences


def compare_enums(
    sync_conn: Connection,
    metadata: MetaData,
    schema: str,
    ignore_tables: frozenset[str] = frozenset(),
) -> list[str]:
    """Compare the values of every native ``Enum`` column in ``metadata`` with its type in the database.

    Alembic's ``compare_metadata()`` never looks at enum members. Values are compared as
    ordered lists, so a value added in the wrong position counts as a difference. The type
    is looked up in ``Enum.schema`` when set, otherwise in ``schema``. Non-native and
    unnamed enums have no type in the database and are skipped; a type in the database
    that no column uses is not reported.

    Args:
        sync_conn: Synchronous SQLAlchemy connection.
        metadata: SQLAlchemy ``MetaData`` of the ORM models.
        schema: PostgreSQL schema the migrations ran in.
        ignore_tables: Table names to skip.

    Returns:
        One line per difference; empty when the enums match.
    """
    inspector = inspect(sync_conn)
    assert isinstance(inspector, PGInspector)
    expected: dict[tuple[str, str], list[str]] = {}
    for table in metadata.sorted_tables:
        if table.name in ignore_tables:
            continue
        for column in table.columns:
            enum = column.type
            if isinstance(enum, Enum) and enum.native_enum and enum.name:
                expected[(enum.schema or schema, enum.name)] = list(enum.enums)
    actual = {(e["schema"], e["name"]): e["labels"] for e in inspector.get_enums(schema="*")}

    differences: list[str] = []
    for (type_schema, name), values in sorted(expected.items()):
        labels = actual.get((type_schema, name))
        if labels is None:
            differences.append(
                f"Enum type '{name}' in schema '{type_schema}' is in the models but not in the database."
            )
        elif labels != values:
            differences.append(f"Enum type '{name}' has values {labels} in the database and {values} in the models.")
    return differences
