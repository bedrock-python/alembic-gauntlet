"""Integration test: the stairway upgrades the head again after its downgrade (issue #53).

The history in ``sample_app_with_drift/alembic/versions/head_downgrade_noop`` ends at a
revision whose ``downgrade()`` forgets to drop the column its ``upgrade()`` adds. The
schema at head matches the models, so every other inherited test passes; only the second
upgrade of the head shows the broken downgrade.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import MetaData
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic_gauntlet import MigrationTestBase
from tests.integration.sample_app_with_drift.models import Base

_SAMPLE_APP = Path(__file__).parent / "sample_app_with_drift"


@pytest.mark.integration
class TestStairwayHeadDowngradeNoop(MigrationTestBase):
    """A no-op downgrade of the newest revision fails the stairway."""

    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config(str(_SAMPLE_APP / "alembic.ini"))
        config.set_main_option("script_location", str(_SAMPLE_APP / "alembic"))
        config.set_main_option("version_locations", str(_SAMPLE_APP / "alembic" / "versions" / "head_downgrade_noop"))
        return config

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata

    async def test_stairway_upgrade_downgrade(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
    ) -> None:
        with pytest.raises(ProgrammingError, match='column "is_active" of relation "users" already exists'):
            await super().test_stairway_upgrade_downgrade(alembic_config, migration_engine, isolated_migration_schema)
