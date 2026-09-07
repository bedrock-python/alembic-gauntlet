"""Integration tests: the three kinds of drift ``compare_metadata()`` misses (issue #37).

One history in four variants, selected through ``version_locations``: the models as
written, a wrong server default, a missing CHECK constraint, and an enum without one of
its values. The clean variant passes every inherited test; each drift variant fails
exactly the test written for it.
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


class _DriftApp(MigrationTestBase):
    variant: ClassVar[str]

    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config(str(_SAMPLE_APP / "alembic.ini"))
        config.set_main_option("script_location", str(_SAMPLE_APP / "alembic"))
        config.set_main_option("version_locations", str(_SAMPLE_APP / "alembic" / "versions" / self.variant))
        return config

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata


@pytest.mark.integration
class TestDriftCleanHistory(_DriftApp):
    """The history that matches the models passes all seven tests, server defaults compared too."""

    variant = "clean"
    migration_diff_compare_server_default = True


@pytest.mark.integration
class TestDriftServerDefaultNotCompared(_DriftApp):
    """With the attribute at its default, a wrong server default is not reported."""

    variant = "server_default"


@pytest.mark.integration
class TestDriftServerDefaultCompared(_DriftApp):
    """With the attribute on, the up-to-date test reports the wrong server default."""

    variant = "server_default"
    migration_diff_compare_server_default = True

    async def test_migrations_up_to_date(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        with pytest.raises(AssertionError, match="is_active"):
            await super().test_migrations_up_to_date(
                alembic_config, migration_engine, isolated_migration_schema, orm_metadata
            )


@pytest.mark.integration
class TestDriftCheckConstraintMissing(_DriftApp):
    """A CHECK constraint the models declare and the migration never created."""

    variant = "check_missing"

    async def test_check_constraints_match(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        with pytest.raises(AssertionError, match="chk_orders_amount_positive"):
            await super().test_check_constraints_match(
                alembic_config, migration_engine, isolated_migration_schema, orm_metadata
            )


@pytest.mark.integration
class TestDriftEnumValueMissing(_DriftApp):
    """An enum created without a value the models have."""

    variant = "enum_value"

    async def test_enum_values_match(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        with pytest.raises(AssertionError, match="order_status"):
            await super().test_enum_values_match(
                alembic_config, migration_engine, isolated_migration_schema, orm_metadata
            )
