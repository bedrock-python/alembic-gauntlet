"""Integration test: a convention template sets both lists of its category (issue #54).

The models' convention has prefix-only templates (``pk_%(table_name)s``,
``fk_%(table_name)s_…``). The ``unnamed_constraints`` history creates ``orders`` with raw
SQL, so PostgreSQL names its keys ``orders_pkey`` and ``orders_user_id_fkey``. Those
names match only the default suffixes, which the convention must replace.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from alembic.config import Config
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic_gauntlet import MigrationTestBase
from tests.integration.sample_app_with_drift.models import Base

_SAMPLE_APP = Path(__file__).parent / "sample_app_with_drift"


class _UnnamedConstraintsApp(MigrationTestBase):
    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config(str(_SAMPLE_APP / "alembic.ini"))
        config.set_main_option("script_location", str(_SAMPLE_APP / "alembic"))
        config.set_main_option("version_locations", str(_SAMPLE_APP / "alembic" / "versions" / "unnamed_constraints"))
        return config

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata


@pytest.mark.integration
class TestNamingPostgresNamesUnderPrefixConvention(_UnnamedConstraintsApp):
    """The names PostgreSQL picks fail the naming test; every other test passes."""

    async def test_naming_conventions(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        with pytest.raises(AssertionError, match=r"'orders_(user_id_fkey|pkey)' on table 'orders'"):
            await super().test_naming_conventions(
                alembic_config, migration_engine, isolated_migration_schema, orm_metadata
            )


@pytest.mark.integration
class TestNamingPostgresNamesAllowedExplicitly(_UnnamedConstraintsApp):
    """Explicit suffix attributes still add PostgreSQL's names next to the convention."""

    allowed_fk_suffixes: ClassVar[list[str]] = ["_fkey"]
    allowed_pk_suffixes: ClassVar[list[str]] = ["_pkey"]
