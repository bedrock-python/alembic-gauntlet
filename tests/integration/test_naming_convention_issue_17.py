"""Integration test: reproduce and verify fix for issue #17.

When MetaData.naming_convention includes both 'ix' and 'uq' keys,
the 'uq_' prefix derived from the 'uq' template should be added to
allowed_index_prefixes (since PostgreSQL creates indexes for unique constraints).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import MetaData

from alembic_gauntlet import MigrationTestBase
from tests.integration.sample_app_with_naming_convention.models import Base

_SAMPLE_APP = Path(__file__).parent / "sample_app_with_naming_convention"


@pytest.mark.integration
class TestNamingConventionWithIxAndUq(MigrationTestBase):
    """Verify that when 'ix' and 'uq' are both defined in naming_convention,
    unique constraint indexes with 'uq_' prefix pass validation.

    Before fix: test_naming_conventions fails because allowed_index_prefixes
    is replaced with only ["ix_"], dropping "uq_".

    After fix: uq_ prefix is added to allowed_index_prefixes automatically.
    """

    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config(str(_SAMPLE_APP / "alembic.ini"))
        config.set_main_option("script_location", str(_SAMPLE_APP / "alembic"))
        return config

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata
