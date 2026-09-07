"""Migration correctness tests mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest
from alembic.autogenerate import compare_metadata
from alembic.operations.ops import MigrateOperation
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from alembic_gauntlet.utils.diff import (
    DEFAULT_IGNORE_TABLES,
    compare_check_constraints,
    compare_enums,
    is_ignored_diff_item,
)
from alembic_gauntlet.utils.migrations import (
    get_all_revisions,
    get_current_revision,
    run_alembic_downgrade,
    run_alembic_upgrade,
)
from alembic_gauntlet.utils.validation import validate_schema_name

if TYPE_CHECKING:
    from alembic.config import Config
    from sqlalchemy import MetaData
    from sqlalchemy.engine import Connection
    from sqlalchemy.ext.asyncio import AsyncEngine

# Type alias for the list returned by compare_metadata().
MigrationDiff = list[tuple[MigrateOperation, ...]]


class MigrationConsistencyMixin:
    """Core migration correctness tests.

    Optional class attributes:
        - ``migration_diff_compare_server_default: bool`` — pass ``compare_server_default``
          to Alembic in ``test_migrations_up_to_date``. Off by default, because a default
          present on one side only — a Python-side ``default=`` in the model, a
          ``server_default`` in the migration — is reported as drift.
    """

    migration_diff_compare_server_default: ClassVar[bool] = False

    async def test_stairway_upgrade_downgrade(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
    ) -> None:
        """Verify every migration can be applied and rolled back individually (stairway test).

        For each revision in chronological order:
        1. Upgrade to this revision.
        2. Assert current revision matches.
        3. Downgrade to the previous revision (or base).
        4. Assert the downgrade succeeded.
        5. Upgrade back before moving to the next step.
        """
        revisions = get_all_revisions(alembic_config)
        if not revisions:
            pytest.skip("No migrations found.")

        for i, revision in enumerate(revisions):
            await run_alembic_upgrade(
                migration_engine, alembic_config, target_schema=isolated_migration_schema, revision=revision
            )
            current = await get_current_revision(migration_engine, target_schema=isolated_migration_schema)
            assert current == revision, f"After upgrade to {revision!r}, got {current!r}."

            target = revisions[i - 1] if i > 0 else "base"
            await run_alembic_downgrade(
                migration_engine, alembic_config, target_schema=isolated_migration_schema, revision=target
            )
            expected = target if target != "base" else None
            current_after = await get_current_revision(migration_engine, target_schema=isolated_migration_schema)
            assert current_after == expected, (
                f"After downgrade from {revision!r} to {target!r}, expected {expected!r}, got {current_after!r}."
            )

            if i < len(revisions) - 1:
                await run_alembic_upgrade(
                    migration_engine, alembic_config, target_schema=isolated_migration_schema, revision=revision
                )

    async def test_migrations_up_to_date(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        """Verify the database schema after a full upgrade matches the SQLAlchemy ORM metadata."""
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
        )

        ignore_tables = DEFAULT_IGNORE_TABLES | frozenset(getattr(self, "migration_diff_ignore_tables", ()))

        def _run_check(sync_conn: Connection) -> MigrationDiff:
            validate_schema_name(isolated_migration_schema, sync_conn)
            quoted = sync_conn.dialect.identifier_preparer.quote_schema(isolated_migration_schema)
            sync_conn.execute(text("SELECT set_config('search_path', :s, true)"), {"s": quoted})
            ctx = MigrationContext.configure(
                sync_conn,
                opts={
                    "version_table_schema": isolated_migration_schema,
                    "compare_server_default": self.migration_diff_compare_server_default,
                },
            )
            diff = compare_metadata(ctx, orm_metadata)
            assert isinstance(diff, list)
            return [d for d in diff if not is_ignored_diff_item(d, ignore_tables)]

        async with migration_engine.connect() as conn:
            diff = await conn.run_sync(_run_check)

        assert not diff, (
            f"Database schema is out of sync with ORM models. Differences:\n{diff}\n"
            "Run: alembic revision --autogenerate"
        )

    async def test_check_constraints_match(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        """Verify the CHECK constraints after a full upgrade match the SQLAlchemy ORM metadata, by name.

        ``compare_metadata()`` never compares CHECK constraints, so a constraint a
        migration forgot is invisible to ``test_migrations_up_to_date``.
        """
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
        )

        ignore_tables = frozenset(getattr(self, "migration_diff_ignore_tables", ()))
        async with migration_engine.connect() as conn:
            differences = await conn.run_sync(
                lambda sc: compare_check_constraints(sc, orm_metadata, isolated_migration_schema, ignore_tables)
            )

        assert not differences, "CHECK constraints are out of sync with ORM models:\n" + "\n".join(differences)

    async def test_enum_values_match(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        """Verify every native ``Enum`` column's values after a full upgrade match the type in the database, in order.

        ``compare_metadata()`` never compares enum members, so a value a migration
        forgot to add is invisible to ``test_migrations_up_to_date``.
        """
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
        )

        ignore_tables = frozenset(getattr(self, "migration_diff_ignore_tables", ()))
        async with migration_engine.connect() as conn:
            differences = await conn.run_sync(
                lambda sc: compare_enums(sc, orm_metadata, isolated_migration_schema, ignore_tables)
            )

        assert not differences, "Enum values are out of sync with ORM models:\n" + "\n".join(differences)

    async def test_single_head_revision(self, alembic_config: Config) -> None:
        """Verify there is exactly one head revision (no unmerged branches)."""
        script = ScriptDirectory.from_config(alembic_config)
        heads = script.get_revisions("heads")
        assert len(heads) == 1, (
            f"Found {len(heads)} head revisions; expected exactly 1. Merge branches with: alembic merge"
        )

    async def test_downgrade_all_the_way(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
    ) -> None:
        """Verify all migrations can be downgraded to base one by one."""
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
            revision="head",
        )

        revisions = get_all_revisions(alembic_config)
        if not revisions:
            pytest.skip("No migrations found.")

        for i, revision in reversed(list(enumerate(revisions))):
            current = await get_current_revision(migration_engine, target_schema=isolated_migration_schema)
            assert current == revision, f"Expected revision {revision!r}, got {current!r}."

            target = revisions[i - 1] if i > 0 else "base"
            await run_alembic_downgrade(
                migration_engine,
                alembic_config,
                target_schema=isolated_migration_schema,
                revision=target,
            )

        final = await get_current_revision(migration_engine, target_schema=isolated_migration_schema)
        assert final is None, f"After full downgrade expected None (base), got {final!r}."
