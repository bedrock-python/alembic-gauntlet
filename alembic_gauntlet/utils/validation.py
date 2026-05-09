"""Schema name validation utilities."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic_gauntlet.exceptions import (
    EmptySchemaNameError,
    InvalidSchemaNameError,
    ReservedWordSchemaNameError,
    SchemaNameTooLongError,
)

_PG_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_PG_MAX_IDENTIFIER_LEN = 63


def validate_schema_name(name: str, connection: Connection | None = None) -> None:
    """Validate a PostgreSQL schema name to prevent SQL injection and ensure sanity.

    Checks format, length, and optionally reserved words (requires a live connection).
    """
    if not name:
        raise EmptySchemaNameError("Schema name cannot be empty.")
    if not _PG_IDENTIFIER_RE.match(name):
        raise InvalidSchemaNameError(
            f"Invalid schema name: {name!r}. "
            "Must start with a letter or underscore and contain only alphanumeric characters and underscores."
        )
    if len(name) > _PG_MAX_IDENTIFIER_LEN:
        raise SchemaNameTooLongError(
            f"Schema name too long: {name!r}. Maximum length is {_PG_MAX_IDENTIFIER_LEN} characters."
        )
    if connection is not None:
        reserved = get_pg_reserved_words(connection)
        if name.lower() in reserved:
            raise ReservedWordSchemaNameError(f"Schema name {name!r} is a PostgreSQL reserved word.")


def get_pg_reserved_words(connection: Connection) -> set[str]:
    """Fetch PostgreSQL reserved keywords from system catalog."""
    result = connection.execute(text("SELECT word FROM pg_get_keywords() WHERE catcode = 'R'"))
    return {row[0].lower() for row in result if row[0]}
