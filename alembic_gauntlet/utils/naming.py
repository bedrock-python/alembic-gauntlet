"""Database naming convention validation."""

from __future__ import annotations

import re
from typing import TypedDict, cast

from sqlalchemy import inspect
from sqlalchemy.engine import Connection


class ForeignKeyInfo(TypedDict, total=False):
    """Foreign key info as returned by ``SQLAlchemy Inspector.get_foreign_keys()``."""

    name: str
    constrained_columns: list[str]
    referred_table: str
    referred_schema: str | None
    referred_columns: list[str]
    options: dict[str, object]


class TableNamingResults(TypedDict):
    """Collected naming data for a single table."""

    indexes: set[str]
    fks: list[ForeignKeyInfo]


def fetch_table_naming_results(
    sync_conn: Connection,
    schema: str,
) -> dict[str, TableNamingResults]:
    """Fetch index and foreign key names for every table in the given schema.

    The ``alembic_version`` table is always excluded.

    Args:
        sync_conn: Synchronous SQLAlchemy connection.
        schema: PostgreSQL schema to inspect.

    Returns:
        Mapping of ``table_name`` → :class:`TableNamingResults`.
    """
    inspector = inspect(sync_conn)
    tables = inspector.get_table_names(schema=schema)

    results: dict[str, TableNamingResults] = {}
    for table in tables:
        if table == "alembic_version":
            continue
        indexes = inspector.get_indexes(table, schema=schema)
        fks = inspector.get_foreign_keys(table, schema=schema)
        results[table] = {
            "indexes": {idx["name"] for idx in indexes if idx["name"]},
            "fks": [cast(ForeignKeyInfo, fk) for fk in fks],
        }

    return results


def validate_naming_results(
    results: dict[str, TableNamingResults],
    allowed_index_prefixes: list[str],
    allowed_index_suffixes: list[str],
    allowed_fk_suffixes: list[str],
    allowed_fk_prefixes: list[str],
) -> None:
    """Assert that every index and foreign key follows naming conventions.

    Index names must match at least one allowed prefix **or** one allowed suffix.
    FK names must match at least one allowed prefix **or** one allowed suffix.
    An optional trailing digit is accepted on suffixes to accommodate PostgreSQL
    partition auto-naming (e.g. ``users_pkey1``).

    Args:
        results: Output of :func:`fetch_table_naming_results`.
        allowed_index_prefixes: Prefixes an index name may start with (e.g. ``["idx_", "uq_"]``).
        allowed_index_suffixes: Suffixes an index name may end with (e.g. ``["_pkey", "_idx"]``).
        allowed_fk_suffixes: Suffixes a foreign key name must end with (e.g. ``["_fkey"]``).
        allowed_fk_prefixes: Prefixes a foreign key name may start with (e.g. ``["fk_"]``).
    """

    prefix_pats = [re.compile(f"^{re.escape(p)}.*") for p in allowed_index_prefixes]
    suffix_pats = [re.compile(f".*{re.escape(s)}\\d*$") for s in allowed_index_suffixes]
    fk_prefix_pats = [re.compile(f"^{re.escape(p)}.*") for p in allowed_fk_prefixes]
    fk_suffix_pats = [re.compile(f".*{re.escape(s)}$") for s in allowed_fk_suffixes]

    for table, data in results.items():
        for idx_name in data["indexes"]:
            valid = any(p.match(idx_name) for p in prefix_pats) or any(p.match(idx_name) for p in suffix_pats)
            assert valid, (
                f"Index '{idx_name}' on table '{table}' does not follow naming conventions. "
                f"Allowed prefixes: {allowed_index_prefixes}, suffixes: {allowed_index_suffixes} "
                "(optional trailing digit permitted)."
            )

        for fk in data["fks"]:
            fk_name = fk.get("name")
            if fk_name:
                valid = any(p.match(fk_name) for p in fk_prefix_pats) or any(p.match(fk_name) for p in fk_suffix_pats)
                assert valid, (
                    f"Foreign key '{fk_name}' on table '{table}' does not follow naming conventions. "
                    f"Allowed prefixes: {allowed_fk_prefixes}, suffixes: {allowed_fk_suffixes}."
                )
