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
          ``allowed_fk_suffixes``, ``allowed_check_prefixes``, ``allowed_check_suffixes``,
          ``allowed_uq_prefixes``, ``allowed_uq_suffixes``, ``allowed_pk_prefixes``,
          ``allowed_pk_suffixes`` — override naming convention rules. When not set,
          rules are auto-derived from ``orm_metadata.naming_convention`` (if present),
          falling back to built-in defaults.

    Example — zero config when ``MetaData`` carries a ``naming_convention``::

        DB_NAMING_CONVENTION = {
            "ix": "%(column_0_label)s_idx",
            "uq": "%(table_name)s_%(column_0_name)s_key",
            "ck": "%(table_name)s_%(constraint_name)s_check",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
            "pk": "%(table_name)s_pkey",
        }
        Base = declarative_base(metadata=MetaData(naming_convention=DB_NAMING_CONVENTION))

        class TestMyMigrations(MigrationTestBase):
            @pytest.fixture
            def orm_metadata(self) -> MetaData:
                return Base.metadata  # naming rules derived automatically

    Example — explicit override::

        class TestMyMigrations(MigrationTestBase):
            migration_diff_ignore_tables = ["events_partitioned_default"]
            allowed_fk_prefixes = ["fk_"]

            @pytest.fixture
            def orm_metadata(self) -> MetaData:
                return Base.metadata
    """

    migration_diff_ignore_tables: ClassVar[list[str]] = []
