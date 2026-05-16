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
    check_constraints: set[str]
    unique_constraints: set[str]
    pk_constraint: str | None


def fetch_table_naming_results(
    sync_conn: Connection,
    schema: str,
) -> dict[str, TableNamingResults]:
    """Fetch index, foreign key, and constraint names for every table in the given schema.

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
        check_constraints = inspector.get_check_constraints(table, schema=schema)
        unique_constraints = inspector.get_unique_constraints(table, schema=schema)
        pk_constraint = inspector.get_pk_constraint(table, schema=schema)

        pk_name: str | None = pk_constraint.get("name") if pk_constraint else None

        results[table] = {
            "indexes": {idx["name"] for idx in indexes if idx["name"]},
            "fks": [cast(ForeignKeyInfo, fk) for fk in fks],
            "check_constraints": {n for c in check_constraints if (n := c.get("name"))},
            "unique_constraints": {n for c in unique_constraints if (n := c.get("name"))},
            "pk_constraint": pk_name,
        }

    return results


def _make_pats(prefixes: list[str], suffixes: list[str]) -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    prefix_pats = [re.compile(f"^{re.escape(p)}.*") for p in prefixes]
    suffix_pats = [re.compile(f".*{re.escape(s)}$") for s in suffixes]
    return prefix_pats, suffix_pats


def _is_valid(name: str, prefix_pats: list[re.Pattern[str]], suffix_pats: list[re.Pattern[str]]) -> bool:
    return any(p.match(name) for p in prefix_pats) or any(p.match(name) for p in suffix_pats)


def validate_naming_results(
    results: dict[str, TableNamingResults],
    allowed_index_prefixes: list[str],
    allowed_index_suffixes: list[str],
    allowed_fk_suffixes: list[str],
    allowed_fk_prefixes: list[str],
    allowed_check_prefixes: list[str],
    allowed_check_suffixes: list[str],
    allowed_uq_prefixes: list[str],
    allowed_uq_suffixes: list[str],
    allowed_pk_prefixes: list[str],
    allowed_pk_suffixes: list[str],
) -> None:
    """Assert that every index, foreign key, and constraint follows naming conventions.

    Each name must match at least one allowed prefix **or** one allowed suffix.
    An optional trailing digit is accepted on index suffixes to accommodate PostgreSQL
    partition auto-naming (e.g. ``users_pkey1``).

    Args:
        results: Output of :func:`fetch_table_naming_results`.
        allowed_index_prefixes: Prefixes an index name may start with (e.g. ``["idx_", "uq_"]``).
        allowed_index_suffixes: Suffixes an index name may end with (e.g. ``["_pkey", "_idx"]``).
        allowed_fk_suffixes: Suffixes a foreign key name must end with (e.g. ``["_fkey"]``).
        allowed_fk_prefixes: Prefixes a foreign key name may start with (e.g. ``["fk_"]``).
        allowed_check_prefixes: Prefixes a check constraint name may start with (e.g. ``["chk_"]``).
        allowed_check_suffixes: Suffixes a check constraint name may end with.
        allowed_uq_prefixes: Prefixes a unique constraint name may start with (e.g. ``["uq_"]``).
        allowed_uq_suffixes: Suffixes a unique constraint name may end with.
        allowed_pk_prefixes: Prefixes a primary key constraint name may start with (e.g. ``["pk_"]``).
        allowed_pk_suffixes: Suffixes a primary key constraint name may end with (e.g. ``["_pkey"]``).
    """
    idx_prefix_pats = [re.compile(f"^{re.escape(p)}.*") for p in allowed_index_prefixes]
    idx_suffix_pats = [re.compile(f".*{re.escape(s)}\\d*$") for s in allowed_index_suffixes]

    fk_prefix_pats, fk_suffix_pats = _make_pats(allowed_fk_prefixes, allowed_fk_suffixes)
    chk_prefix_pats, chk_suffix_pats = _make_pats(allowed_check_prefixes, allowed_check_suffixes)
    uq_prefix_pats, uq_suffix_pats = _make_pats(allowed_uq_prefixes, allowed_uq_suffixes)
    pk_prefix_pats, pk_suffix_pats = _make_pats(allowed_pk_prefixes, allowed_pk_suffixes)

    for table, data in results.items():
        for idx_name in data["indexes"]:
            valid = any(p.match(idx_name) for p in idx_prefix_pats) or any(p.match(idx_name) for p in idx_suffix_pats)
            assert valid, (
                f"Index '{idx_name}' on table '{table}' does not follow naming conventions. "
                f"Allowed prefixes: {allowed_index_prefixes}, suffixes: {allowed_index_suffixes} "
                "(optional trailing digit permitted)."
            )

        for fk in data["fks"]:
            fk_name = fk.get("name")
            if fk_name:
                assert _is_valid(fk_name, fk_prefix_pats, fk_suffix_pats), (
                    f"Foreign key '{fk_name}' on table '{table}' does not follow naming conventions. "
                    f"Allowed prefixes: {allowed_fk_prefixes}, suffixes: {allowed_fk_suffixes}."
                )

        for chk_name in data["check_constraints"]:
            assert _is_valid(chk_name, chk_prefix_pats, chk_suffix_pats), (
                f"Check constraint '{chk_name}' on table '{table}' does not follow naming conventions. "
                f"Allowed prefixes: {allowed_check_prefixes}, suffixes: {allowed_check_suffixes}."
            )

        for uq_name in data["unique_constraints"]:
            assert _is_valid(uq_name, uq_prefix_pats, uq_suffix_pats), (
                f"Unique constraint '{uq_name}' on table '{table}' does not follow naming conventions. "
                f"Allowed prefixes: {allowed_uq_prefixes}, suffixes: {allowed_uq_suffixes}."
            )

        pk_name = data["pk_constraint"]
        if pk_name:
            assert _is_valid(pk_name, pk_prefix_pats, pk_suffix_pats), (
                f"Primary key '{pk_name}' on table '{table}' does not follow naming conventions. "
                f"Allowed prefixes: {allowed_pk_prefixes}, suffixes: {allowed_pk_suffixes}."
            )
