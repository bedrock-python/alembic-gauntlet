"""Schema diff filtering for migration consistency tests."""

from __future__ import annotations

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
