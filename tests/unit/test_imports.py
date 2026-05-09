"""Unit tests for public API imports."""

import pytest


@pytest.mark.unit
def test__main_module__imports() -> None:
    # Act
    import alembic_gauntlet  # noqa: PLC0415

    # Assert - check all public exports exist
    assert hasattr(alembic_gauntlet, "MigrationTestBase")
    assert hasattr(alembic_gauntlet, "run_alembic_upgrade")
    assert hasattr(alembic_gauntlet, "run_alembic_downgrade")
    assert hasattr(alembic_gauntlet, "get_current_revision")
    assert hasattr(alembic_gauntlet, "get_all_revisions")
    assert hasattr(alembic_gauntlet, "create_isolated_migration_schema")
    assert hasattr(alembic_gauntlet, "EmptySchemaNameError")
    assert hasattr(alembic_gauntlet, "InvalidSchemaNameError")
    assert hasattr(alembic_gauntlet, "SchemaNameTooLongError")


@pytest.mark.unit
def test__testing_module__imports() -> None:
    # Act
    from alembic_gauntlet import testing  # noqa: PLC0415

    # Assert
    assert hasattr(testing, "MigrationTestBase")
    assert hasattr(testing, "MigrationSchemaMixin")
    assert hasattr(testing, "MigrationConsistencyMixin")
    assert hasattr(testing, "MigrationNamingMixin")
    assert hasattr(testing, "MigrationDiff")


@pytest.mark.unit
def test__version__import() -> None:
    # Act
    from alembic_gauntlet.__version__ import __version__  # noqa: PLC0415

    # Assert
    assert isinstance(__version__, str)
    assert len(__version__) > 0


@pytest.mark.unit
def test__all__exports() -> None:
    # Act
    import alembic_gauntlet  # noqa: PLC0415

    # Assert
    assert hasattr(alembic_gauntlet, "__all__")
    assert isinstance(alembic_gauntlet.__all__, list)
    assert "MigrationTestBase" in alembic_gauntlet.__all__
