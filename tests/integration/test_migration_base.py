"""Integration tests: verify MigrationTestBase works end-to-end with the sample app."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import MetaData

from alembic_gauntlet import MigrationTestBase
from tests.integration.sample_app.models import Base

_SAMPLE_APP = Path(__file__).parent / "sample_app"


@pytest.mark.integration
class TestSampleMigrations(MigrationTestBase):
    """Run all five MigrationTestBase checks against the sample app migrations.

    Tests inherited:
    - test_stairway_upgrade_downgrade
    - test_migrations_up_to_date
    - test_single_head_revision
    - test_downgrade_all_the_way
    - test_naming_conventions
    """

    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config(str(_SAMPLE_APP / "alembic.ini"))
        config.set_main_option("script_location", str(_SAMPLE_APP / "alembic"))
        return config

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata
