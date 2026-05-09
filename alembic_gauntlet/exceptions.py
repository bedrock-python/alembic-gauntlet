"""Exception classes for alembic-gauntlet."""


class SchemaValidationError(Exception):
    """Base for schema name validation errors."""


class EmptySchemaNameError(SchemaValidationError):
    """Schema name is empty."""


class InvalidSchemaNameError(SchemaValidationError):
    """Schema name has invalid format."""


class ReservedWordSchemaNameError(SchemaValidationError):
    """Schema name is a PostgreSQL reserved word."""


class SchemaNameTooLongError(SchemaValidationError):
    """Schema name exceeds the PostgreSQL maximum identifier length of 63 characters."""
