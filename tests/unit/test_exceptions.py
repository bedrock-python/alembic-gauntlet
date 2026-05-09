"""Unit tests for custom exceptions."""

import pytest

from alembic_gauntlet.exceptions import (
    EmptySchemaNameError,
    InvalidSchemaNameError,
    ReservedWordSchemaNameError,
    SchemaNameTooLongError,
    SchemaValidationError,
)


@pytest.mark.unit
def test__empty_schema_name_error__is_schema_validation_error() -> None:
    # Arrange & Act
    error = EmptySchemaNameError("test message")

    # Assert
    assert isinstance(error, SchemaValidationError)
    assert "test message" in str(error)


@pytest.mark.unit
def test__invalid_schema_name_error__is_schema_validation_error() -> None:
    # Arrange & Act
    error = InvalidSchemaNameError("invalid schema")

    # Assert
    assert isinstance(error, SchemaValidationError)
    assert "invalid schema" in str(error)


@pytest.mark.unit
def test__schema_name_too_long_error__is_schema_validation_error() -> None:
    # Arrange & Act
    error = SchemaNameTooLongError("long name")

    # Assert
    assert isinstance(error, SchemaValidationError)
    assert "long name" in str(error)


@pytest.mark.unit
def test__reserved_word_schema_name_error__is_schema_validation_error() -> None:
    # Arrange & Act
    error = ReservedWordSchemaNameError("select is reserved")

    # Assert
    assert isinstance(error, SchemaValidationError)
    assert "select is reserved" in str(error)
