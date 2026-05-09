"""Schema isolation mixin for migration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from alembic_gauntlet.utils.migrations import create_isolated_migration_schema

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class MigrationSchemaMixin:
    """Provides the ``isolated_migration_schema`` fixture."""

    @pytest.fixture
    async def isolated_migration_schema(
        self,
        migration_db_url: str,
    ) -> AsyncGenerator[str, None]:
        """Create a unique PostgreSQL schema for this test run and drop it afterwards."""
        async for schema in create_isolated_migration_schema(migration_db_url):
            yield schema
