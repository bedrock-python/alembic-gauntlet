"""Unit tests for schema name validation."""

import pytest

from alembic_gauntlet.exceptions import (
    EmptySchemaNameError,
    InvalidSchemaNameError,
    SchemaNameTooLongError,
)
from alembic_gauntlet.utils.validation import validate_schema_name


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema_name",
    [
        "public",
        "_private_schema",
        "test_mig_abc123",
        "a" * 63,  # exactly max length
    ],
    ids=["simple", "underscore_prefix", "alphanumeric_underscores", "max_length_63"],
)
def test__validate_schema_name__valid_name__passes(schema_name: str) -> None:
    # Arrange & Act & Assert
    validate_schema_name(schema_name)


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema_name",
    [
        "1schema",
        "my-schema",
        "my schema",
        "my.schema",
        "public; DROP TABLE users--",
        "schema;drop",
    ],
    ids=[
        "starts_with_digit",
        "contains_hyphen",
        "contains_space",
        "contains_dot",
        "sql_injection",
        "contains_semicolon",
    ],
)
def test__validate_schema_name__invalid_format__raises_invalid_error(schema_name: str) -> None:
    # Arrange & Act & Assert
    with pytest.raises(InvalidSchemaNameError):
        validate_schema_name(schema_name)


@pytest.mark.unit
def test__validate_schema_name__empty_string__raises_empty_error() -> None:
    # Arrange
    schema_name = ""

    # Act & Assert
    with pytest.raises(EmptySchemaNameError):
        validate_schema_name(schema_name)


@pytest.mark.unit
def test__validate_schema_name__exceeds_max_length__raises_too_long_error() -> None:
    # Arrange
    schema_name = "a" * 64

    # Act & Assert
    with pytest.raises(SchemaNameTooLongError):
        validate_schema_name(schema_name)


@pytest.mark.unit
def test__validate_schema_name__reserved_word_without_connection__skips_check() -> None:
    # Arrange
    # "select" is a PostgreSQL reserved word, but without a connection we cannot check it
    schema_name = "select"

    # Act & Assert
    validate_schema_name(schema_name)
