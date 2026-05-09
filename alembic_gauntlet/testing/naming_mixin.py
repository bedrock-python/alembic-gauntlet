"""Naming convention tests mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from alembic_gauntlet.utils.migrations import run_alembic_upgrade
from alembic_gauntlet.utils.naming import fetch_table_naming_results, validate_naming_results

if TYPE_CHECKING:
    from alembic.config import Config
    from sqlalchemy.ext.asyncio import AsyncEngine


class MigrationNamingMixin:
    """Naming convention tests for database objects."""

    allowed_index_prefixes: ClassVar[list[str]] = ["idx_", "uq_"]
    allowed_index_suffixes: ClassVar[list[str]] = ["_idx", "_pkey", "_key"]
    allowed_fk_suffixes: ClassVar[list[str]] = ["_fkey"]

    async def test_naming_conventions(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
    ) -> None:
        """Verify indexes and foreign keys follow naming conventions after a full upgrade."""
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
        )

        async with migration_engine.connect() as conn:
            results = await conn.run_sync(lambda sc: fetch_table_naming_results(sc, schema=isolated_migration_schema))

        ignore_tables = set(getattr(self, "migration_diff_ignore_tables", []))
        filtered = {t: r for t, r in results.items() if t not in ignore_tables}

        validate_naming_results(
            filtered,
            allowed_index_prefixes=self.allowed_index_prefixes,
            allowed_index_suffixes=self.allowed_index_suffixes,
            allowed_fk_suffixes=self.allowed_fk_suffixes,
        )
