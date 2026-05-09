"""Alembic env.py for the sample app integration tests.

Demonstrates the recommended pattern: read ``target_schema`` from
``config.attributes`` (set by alembic-gauntlet) with no import from the library.
"""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.sample_app.models import Base

config = context.config

# alembic-gauntlet sets config.attributes["target_schema"] before calling upgrade/downgrade.
# Fall back to the env var or "public" for standalone (non-test) runs.
target_schema: str = config.attributes.get("target_schema") or os.getenv("MIGRATION_SCHEMA", "public")

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    if target_schema != "public":
        connection.execute(text(f'SET search_path TO "{target_schema}"'))

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=target_schema,
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url", "")
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if config.attributes.get("connection") is not None:
    # Called from alembic-gauntlet: connection is already provided.
    do_run_migrations(config.attributes["connection"])
else:
    asyncio.run(run_migrations_online())
