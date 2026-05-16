"""Base class combining all migration test mixins."""

from __future__ import annotations

from typing import ClassVar

from alembic_gauntlet.testing.consistency_mixin import MigrationConsistencyMixin
from alembic_gauntlet.testing.naming_mixin import MigrationNamingMixin
from alembic_gauntlet.testing.schema_mixin import MigrationSchemaMixin


class MigrationTestBase(
    MigrationSchemaMixin,
    MigrationConsistencyMixin,
    MigrationNamingMixin,
):
    """Base class for database migration tests.

    Inherit from this class and provide the following fixtures to get all five
    migration tests for free:

    Required fixtures:
        - ``migration_db_url: str`` — async DSN to the test database.
        - ``orm_metadata: MetaData`` — SQLAlchemy metadata of your ORM models.

    Auto-provided fixtures (override if needed):
        - ``alembic_config`` — reads ``alembic.ini`` from the current directory.
        - ``migration_engine`` — async engine with NullPool.
        - ``isolated_migration_schema`` — unique schema per test, auto-dropped.

    Optional class attributes:
        - ``migration_diff_ignore_tables: list[str]`` — table names to exclude from
          schema diff and naming checks (e.g. auto-generated partition tables).
        - ``allowed_index_prefixes``, ``allowed_index_suffixes``, ``allowed_fk_prefixes``,
          ``allowed_fk_suffixes`` — override naming convention rules.

    Example::

        class TestMyMigrations(MigrationTestBase):
            migration_diff_ignore_tables = ["events_partitioned_default"]

            @pytest.fixture
            def orm_metadata(self) -> MetaData:
                return Base.metadata
    """

    migration_diff_ignore_tables: ClassVar[list[str]] = []
