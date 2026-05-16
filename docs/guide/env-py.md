# Configuring env.py

Alembic's `env.py` is the bridge between your application and the migration engine.
`alembic-gauntlet` injects a `connection` and a `target_schema` into
`alembic_config.attributes` before running each test — your `env.py` must read
those values so the library can drive migrations into isolated schemas.

## How alembic-gauntlet communicates with env.py

Before calling `alembic upgrade` / `alembic downgrade`, the library sets:

| Key | Type | Description |
|-----|------|-------------|
| `config.attributes["connection"]` | `sqlalchemy.engine.Connection` | Ready-to-use sync connection. If present, skip engine creation and use this directly. |
| `config.attributes["target_schema"]` | `str` | Schema to migrate into (e.g. `test_mig_a1b2c3d4`). Fall back to `MIGRATION_SCHEMA` env var or `"public"`. |

Both are cleaned up automatically after each test run.

## Minimal env.py

```python
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

config = context.config

# Support injected schema (alembic-gauntlet) or env var override
target_schema = config.attributes.get("target_schema") or os.getenv("MIGRATION_SCHEMA", "public")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your ORM metadata here
from myapp.db import Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=target_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    if target_schema != "public":
        from sqlalchemy import text
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"'))
        # SET LOCAL — scoped to the current transaction only.
        # Never use plain SET here: it would persist on the connection after
        # it is returned to the pool and corrupt search_path for other callers.
        connection.execute(text(f'SET LOCAL search_path TO "{target_schema}"'))

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=target_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    url = config.get_main_option("sqlalchemy.url")
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # alembic-gauntlet injects a ready connection — use it directly
    if config.attributes.get("connection") is not None:
        do_run_migrations(config.attributes["connection"])
    else:
        asyncio.run(run_migrations_online())
```

## Critical: SET LOCAL, not SET

!!! danger "Never use plain `SET search_path` in migrations"
    ```python
    # ❌ WRONG — persists on the connection after it returns to the pool
    connection.execute(text(f'SET search_path TO "{target_schema}"'))

    # ✅ CORRECT — scoped to the current transaction only
    connection.execute(text(f'SET LOCAL search_path TO "{target_schema}"'))
    ```

    Plain `SET` changes the session-level `search_path`. When the connection is
    returned to a connection pooler (PgBouncer, pgpool, SQLAlchemy's own pool),
    it carries the altered `search_path` into the next caller's query — silently
    routing their queries to the wrong schema.

    `SET LOCAL` is automatically rolled back when the transaction ends, so the
    connection is always returned to the pool in a clean state.

## Handling non-public schemas

The `do_run_migrations` function above creates the schema if it doesn't exist and
sets `search_path` locally. This is exactly what `alembic-gauntlet` relies on when
it creates an isolated `test_mig_*` schema for each test.

For the `public` schema you can skip both steps — PostgreSQL's default
`search_path` already includes `public`.

## Advisory locks

For services with multiple replicas, take a PostgreSQL advisory lock before
running migrations to prevent concurrent execution:

```python
import hashlib

# Generate a stable 64-bit lock ID from your service name.
# Use SHA-256 (not CRC32) to minimise collision risk across services.
_hash = hashlib.sha256(b"myapp_migrations").digest()
MIGRATIONS_LOCK_ID = int.from_bytes(_hash[:8], "big", signed=True)


def do_run_migrations(connection: Connection) -> None:
    if target_schema != "public":
        from sqlalchemy import text
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"'))
        connection.execute(text(f'SET LOCAL search_path TO "{target_schema}"'))

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=target_schema,
    )
    with context.begin_transaction():
        from sqlalchemy import text
        connection.execute(text(f"SELECT pg_advisory_xact_lock({MIGRATIONS_LOCK_ID})"))
        context.run_migrations()
```

`pg_advisory_xact_lock` is released automatically when the transaction ends —
no explicit unlock needed.

## Filtering autogenerate output

If you use partitioned tables or extension-owned tables, filter them out of
`alembic revision --autogenerate` with `include_object`:

```python
from typing import Any


def include_object(
    obj: Any, name: str, type_: str, reflected: bool, compare_to: Any
) -> bool:
    if type_ == "table":
        if name == "alembic_version":
            return False
        # Exclude default partitions and auto-generated partition tables
        if "_default" in name or "partitioned_default" in name:
            return False
    if type_ == "index":
        if hasattr(obj, "table") and obj.table is not None:
            if "_default" in obj.table.name or "partitioned_default" in obj.table.name:
                return False
    return True
```

Pass it to `context.configure`:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    version_table_schema=target_schema,
    include_object=include_object,
    include_schemas=False,
)
```

## Loading database credentials

`env.py` is responsible for building the database URL. A common pattern is to
load settings from environment variables via a Pydantic settings model:

```python
import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    user: str
    password: str
    name: str

    model_config = {"env_prefix": "DB_"}

    def to_async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


db_settings = DBSettings()
```

Then in `run_migrations_online`:

```python
async def run_migrations_online() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(db_settings.to_async_dsn(), poolclass=NullPool)
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()
```

Use `NullPool` in migrations — you never want migration connections to be reused
or kept alive after the migration completes.
