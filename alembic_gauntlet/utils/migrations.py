"""Migration runner and schema isolation utilities."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic_gauntlet.utils.validation import validate_schema_name


async def run_alembic_upgrade(
    engine: AsyncEngine,
    alembic_config: Config,
    target_schema: str = "public",
    revision: str = "head",
) -> None:
    """Run ``alembic upgrade`` programmatically without spawning a subprocess.

    Args:
        engine: Async SQLAlchemy engine.
        alembic_config: Alembic config object (typically from ``alembic.ini``).
        target_schema: PostgreSQL schema to run migrations in. Defaults to ``"public"``.
        revision: Target revision identifier. Defaults to ``"head"``.
    """

    def _upgrade(sync_conn: Connection) -> None:
        validate_schema_name(target_schema, sync_conn)
        alembic_config.attributes["target_schema"] = target_schema
        alembic_config.attributes["connection"] = sync_conn
        try:
            command.upgrade(alembic_config, revision)
        finally:
            alembic_config.attributes.pop("connection", None)

    async with engine.begin() as conn:
        await conn.run_sync(_upgrade)


async def run_alembic_downgrade(
    engine: AsyncEngine,
    alembic_config: Config,
    target_schema: str = "public",
    revision: str = "base",
) -> None:
    """Run ``alembic downgrade`` programmatically without spawning a subprocess.

    Args:
        engine: Async SQLAlchemy engine.
        alembic_config: Alembic config object.
        target_schema: PostgreSQL schema to run migrations in. Defaults to ``"public"``.
        revision: Target revision identifier. Defaults to ``"base"``.
    """

    def _downgrade(sync_conn: Connection) -> None:
        validate_schema_name(target_schema, sync_conn)
        alembic_config.attributes["target_schema"] = target_schema
        alembic_config.attributes["connection"] = sync_conn
        try:
            command.downgrade(alembic_config, revision)
        finally:
            alembic_config.attributes.pop("connection", None)

    async with engine.begin() as conn:
        await conn.run_sync(_downgrade)


async def get_current_revision(
    engine: AsyncEngine,
    target_schema: str = "public",
) -> str | None:
    """Return the current Alembic revision for the given schema, or ``None`` if at base.

    Args:
        engine: Async SQLAlchemy engine.
        target_schema: PostgreSQL schema to inspect. Defaults to ``"public"``.
    """

    def _get_rev(sync_conn: Connection) -> str | None:
        validate_schema_name(target_schema, sync_conn)
        ctx = MigrationContext.configure(
            sync_conn,
            opts={"version_table_schema": target_schema},
        )
        return ctx.get_current_revision()  # type: ignore[no-any-return]

    async with engine.connect() as conn:
        return await conn.run_sync(_get_rev)


def get_all_revisions(alembic_config: Config) -> list[str]:
    """Return all migration revision IDs in chronological order (base → head).

    Args:
        alembic_config: Alembic config object.
    """
    script = ScriptDirectory.from_config(alembic_config)
    # walk_revisions() yields head → base; reverse for base → head order.
    revisions = [rev.revision for rev in script.walk_revisions() if rev.revision]
    return list(reversed(revisions))


async def create_isolated_migration_schema(
    migration_db_url: str,
) -> AsyncGenerator[str, None]:
    """Create a unique PostgreSQL schema for one test run, yield it, then drop it.

    Uses a dedicated engine so that schema creation and deletion do not interfere
    with the connection pool used by the migration engine.

    Schema name format: ``test_mig_{8-char hex}``.

    Args:
        migration_db_url: Async DSN for the test database.

    Yields:
        The name of the freshly created schema.
    """
    schema = f"test_mig_{uuid.uuid4().hex[:8]}"
    validate_schema_name(schema)

    engine = create_async_engine(migration_db_url, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(CreateSchema(schema))
            await conn.commit()

        yield schema

    finally:
        async with engine.connect() as conn:
            await conn.execute(DropSchema(schema, cascade=True, if_exists=True))
            await conn.commit()
        await engine.dispose()
