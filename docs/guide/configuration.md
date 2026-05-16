# Configuration

`alembic-gauntlet` provides several configuration options to customize test behavior.

## Required fixtures

### orm_metadata

**Purpose**: Provides SQLAlchemy metadata for schema consistency checks.

```python
from sqlalchemy import MetaData
import pytest


@pytest.fixture
def orm_metadata(self) -> MetaData:
    from myapp.db import Base
    return Base.metadata
```

**When to use**: Always required for `test_migrations_up_to_date` and `test_naming_conventions`.

### migration_db_url

**Purpose**: Database connection URL for running migrations.

```python
@pytest.fixture(scope="session")
def migration_db_url(self) -> str:
    return "postgresql+asyncpg://user:pass@localhost:5432/testdb"
```

**Scope**: Typically `session` to reuse the database URL across all tests.

**Formats**:
- `postgresql+asyncpg://user:pass@host:port/dbname` (recommended)
- `postgresql+psycopg://user:pass@host:port/dbname`
- `postgresql://user:pass@host:port/dbname`

## Optional fixtures

### alembic_config

**Purpose**: Customize Alembic configuration.

```python
from alembic.config import Config


@pytest.fixture
def alembic_config(self) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "myapp/migrations")
    return config
```

**Default behavior**: Automatically discovers `alembic.ini` in project root.

**Use cases**:
- Non-standard Alembic config location
- Dynamic configuration per environment
- Multiple migration directories

### migration_engine

**Purpose**: Provide custom AsyncEngine for migrations.

```python
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


@pytest.fixture
async def migration_engine(self, migration_db_url: str) -> AsyncEngine:
    engine = create_async_engine(
        migration_db_url,
        poolclass=NullPool,
        echo=True,  # Log all SQL
    )
    try:
        yield engine
    finally:
        await engine.dispose()
```

**Use cases**:
- Custom pool configuration
- SQL query logging
- Connection middleware

## Class attributes

### migration_diff_ignore_tables

**Purpose**: Ignore specific tables in schema consistency checks.

```python
from typing import ClassVar


class TestMyMigrations(MigrationTestBase):
    migration_diff_ignore_tables: ClassVar[list[str]] = ["alembic_version", "events_default"]
```

**Default**: `["alembic_version"]`

**Use cases**:
- Partitioned tables not managed by Alembic
- External tables (e.g., PostGIS extension tables)
- Temporary tables

### allowed_index_prefixes

**Purpose**: Allowed prefixes for index names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_index_prefixes: ClassVar[list[str]] = ["idx_", "uq_", "ix_"]
```

**Default**: `["idx_", "uq_"]`

**Examples**:
- `idx_users_email` ✅
- `uq_users_email` ✅
- `ix_users_email` ✅ (if `"ix_"` is in the list)
- `users_email_idx` ❌ (wrong location)

### allowed_index_suffixes

**Purpose**: Allowed suffixes for index names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_index_suffixes: ClassVar[list[str]] = ["_idx", "_pkey", "_key", "_uniq"]
```

**Default**: `["_idx", "_pkey", "_key"]`

**Examples**:
- `users_email_idx` ✅
- `users_pkey` ✅
- `users_email_key` ✅
- `users_email_index` ❌ (wrong suffix)

### allowed_fk_prefixes

**Purpose**: Allowed prefixes for foreign key names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_fk_prefixes: ClassVar[list[str]] = ["fk_"]
```

**Default**: `["fk_"]`

**Examples**:
- `fk_profiles_user_id_users` ✅
- `profiles_user_id_fkey` ❌ (no prefix match, checked against suffixes)

### allowed_fk_suffixes

**Purpose**: Allowed suffixes for foreign key names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_fk_suffixes: ClassVar[list[str]] = ["_fkey", "_fk"]
```

**Default**: `["_fkey"]`

**Examples**:
- `profiles_user_id_fkey` ✅
- `profiles_user_id_fk` ✅ (if `"_fk"` is in the list)
- `profiles_user_id_foreign` ❌

### allowed_check_prefixes / allowed_check_suffixes

**Purpose**: Allowed prefixes and suffixes for CHECK constraint names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_check_prefixes: ClassVar[list[str]] = ["chk_"]
    allowed_check_suffixes: ClassVar[list[str]] = ["_check"]
```

**Defaults**: prefixes `["chk_"]`, suffixes `[]`

**Examples**:
- `chk_orders_amount_positive` ✅
- `orders_amount_check` ❌ (no suffix in defaults — add `"_check"` to enable)

### allowed_uq_prefixes / allowed_uq_suffixes

**Purpose**: Allowed prefixes and suffixes for UNIQUE constraint names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_uq_prefixes: ClassVar[list[str]] = ["uq_"]
    allowed_uq_suffixes: ClassVar[list[str]] = ["_key"]
```

**Defaults**: prefixes `["uq_"]`, suffixes `[]`

**Examples**:
- `uq_users_email` ✅
- `users_email_key` ❌ (no suffix in defaults — add `"_key"` to enable)

### allowed_pk_prefixes / allowed_pk_suffixes

**Purpose**: Allowed prefixes and suffixes for PRIMARY KEY constraint names.

```python
class TestMyMigrations(MigrationTestBase):
    allowed_pk_prefixes: ClassVar[list[str]] = ["pk_"]
    allowed_pk_suffixes: ClassVar[list[str]] = ["_pkey"]
```

**Defaults**: prefixes `["pk_"]`, suffixes `["_pkey"]`

**Examples**:
- `pk_users` ✅
- `users_pkey` ✅
- `users_pk` ❌

## Auto-deriving rules from MetaData.naming_convention

If your SQLAlchemy `MetaData` already carries a `naming_convention`, you don't
need to set any class attributes — `alembic-gauntlet` extracts the rules
automatically.

```python
DB_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
Base = declarative_base(metadata=MetaData(naming_convention=DB_NAMING_CONVENTION))


class TestMyMigrations(MigrationTestBase):
    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata  # naming rules derived automatically — no class attrs needed
```

### Resolution order (last wins)

| Layer | Source | Notes |
|-------|--------|-------|
| 1 | Built-in defaults | Always present as a baseline |
| 2 | `MetaData.naming_convention` | Overrides defaults when non-empty templates are found |
| 3 | Explicit class attributes | Always wins — set only what you want to override |

Layer 2 extracts the literal prefix (text before the first `%(`) and the literal
suffix (text after the last `)s`) from each template. Fully dynamic templates
like `"%(table_name)s_%(column_0_name)s"` produce no prefix or suffix and are
silently ignored.

## Complete example

```python
import pytest
from typing import ClassVar
from alembic.config import Config
from alembic_gauntlet import MigrationTestBase
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.mark.integration
class TestMyMigrations(MigrationTestBase):
    """Fully configured migration tests."""

    # Customize ignored tables
    migration_diff_ignore_tables: ClassVar[list[str]] = [
        "alembic_version",
        "spatial_ref_sys",  # PostGIS table
        "events_default",   # Partitioned table
    ]

    # Customize naming conventions
    allowed_index_prefixes: ClassVar[list[str]] = ["idx_", "uq_", "ix_"]
    allowed_index_suffixes: ClassVar[list[str]] = ["_idx", "_pkey", "_key", "_uniq"]
    allowed_fk_suffixes: ClassVar[list[str]] = ["_fkey", "_fk"]

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        from myapp.db import Base
        return Base.metadata

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        # Use environment variable in CI
        import os
        return os.getenv(
            "TEST_DB_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
        )

    @pytest.fixture
    def alembic_config(self) -> Config:
        config = Config("alembic.ini")
        # Override script location if needed
        config.set_main_option("script_location", "myapp/alembic")
        return config

    @pytest.fixture
    async def migration_engine(self, migration_db_url: str) -> AsyncEngine:
        engine = create_async_engine(
            migration_db_url,
            poolclass=NullPool,
            echo=False,  # Set to True to debug SQL
        )
        try:
            yield engine
        finally:
            await engine.dispose()
```

## Environment-specific configuration

### Development vs CI

```python
import os
import pytest


@pytest.fixture(scope="session")
def migration_db_url(self) -> str:
    if os.getenv("CI"):
        # CI environment (GitHub Actions, GitLab CI, etc.)
        return "postgresql+asyncpg://postgres:postgres@postgres:5432/test_db"
    else:
        # Local development
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
```

### Multiple databases

```python
@pytest.fixture(scope="session", params=["postgresql", "cockroachdb"])
def migration_db_url(self, request) -> str:
    db_urls = {
        "postgresql": "postgresql+asyncpg://user:pass@localhost:5432/test_db",
        "cockroachdb": "cockroachdb+asyncpg://root@localhost:26257/test_db",
    }
    return db_urls[request.param]
```

## Disabling specific tests

### Skip naming convention test

```python
@pytest.mark.skip(reason="Custom naming conventions not yet enforced")
async def test_naming_conventions(self, *args, **kwargs):
    pass
```

### Skip stairway test for specific revision

```python
async def test_stairway_upgrade_downgrade(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Override to skip problematic revisions."""
    revisions = await get_all_revisions(alembic_config)
    
    for revision in revisions:
        if revision == "abc123":  # Skip specific revision
            continue
        
        # Run stairway test for this revision
        await run_alembic_upgrade(alembic_config, migration_engine, revision)
        await run_alembic_downgrade(alembic_config, migration_engine, "-1")
        await run_alembic_upgrade(alembic_config, migration_engine, revision)
```

## Pytest markers

### Custom markers for migration tests

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: integration tests requiring database",
    "migrations: migration-specific tests",
    "slow: slow tests that may take several seconds",
]
```

```python
@pytest.mark.integration
@pytest.mark.migrations
@pytest.mark.slow
class TestMyMigrations(MigrationTestBase):
    ...
```

Run only migration tests:

```bash
pytest -m migrations
```

## Parallel execution

`alembic-gauntlet` supports parallel test execution with `pytest-xdist`:

```bash
pip install pytest-xdist
pytest -n auto tests/migrations/
```

Each test gets an isolated PostgreSQL schema, so tests don't interfere.

**Note**: Requires unique schema names per test run (handled automatically).

## Logging and debugging

### Enable SQL logging

```python
@pytest.fixture
async def migration_engine(self, migration_db_url: str) -> AsyncEngine:
    engine = create_async_engine(
        migration_db_url,
        poolclass=NullPool,
        echo=True,  # Log all SQL statements
    )
    try:
        yield engine
    finally:
        await engine.dispose()
```

### Enable Alembic logging

```python
import logging


@pytest.fixture(autouse=True)
def setup_logging(self):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("alembic").setLevel(logging.DEBUG)
```

## Next steps

- [Configuring env.py](env-py.md) — connect alembic-gauntlet to your migrations
- [Advanced usage](advanced.md) — custom validations, mixins
- [API reference](../reference/index.md) — complete API docs
