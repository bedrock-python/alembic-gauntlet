# Advanced usage

Advanced patterns for power users and complex scenarios.

## Using individual mixins

Instead of `MigrationTestBase`, you can compose only the mixins you need.

### Schema mixin only

```python
from alembic_gauntlet.testing import MigrationSchemaMixin


class TestCustomMigrations(MigrationSchemaMixin):
    """Only provides isolated schema fixture."""

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        return "postgresql+asyncpg://user:pass@localhost:5432/testdb"

    async def test_custom_migration_logic(
        self,
        isolated_migration_schema: str,
    ) -> None:
        """Your custom test using isolated schema."""
        assert isolated_migration_schema.startswith("test_mig_")
```

### Consistency tests only

```python
from alembic_gauntlet.testing import MigrationConsistencyMixin, MigrationSchemaMixin


class TestConsistency(MigrationSchemaMixin, MigrationConsistencyMixin):
    """Only schema consistency tests, no naming validation."""

    @pytest.fixture
    def orm_metadata(self):
        from myapp.db import Base
        return Base.metadata

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        return "postgresql+asyncpg://user:pass@localhost:5432/testdb"
```

Now you get:
- ✅ `test_stairway_upgrade_downgrade`
- ✅ `test_migrations_up_to_date`
- ✅ `test_single_head_revision`
- ✅ `test_downgrade_all_the_way`
- ❌ `test_naming_conventions` (not included)

### Naming tests only

```python
from alembic_gauntlet.testing import MigrationSchemaMixin, MigrationNamingMixin


class TestNaming(MigrationSchemaMixin, MigrationNamingMixin):
    """Only naming convention validation."""

    @pytest.fixture
    def orm_metadata(self):
        from myapp.db import Base
        return Base.metadata

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        return "postgresql+asyncpg://user:pass@localhost:5432/testdb"
```

## Custom validation logic

### Add custom post-migration checks

```python
from alembic_gauntlet import MigrationTestBase
from sqlalchemy import text


class TestWithCustomChecks(MigrationTestBase):
    async def test_custom_data_validation(
        self,
        isolated_migration_schema: str,
        migration_engine: AsyncEngine,
        alembic_config: Config,
    ) -> None:
        """Validate specific data constraints after migration."""
        # Run migrations
        await run_alembic_upgrade(alembic_config, migration_engine, "head")

        # Check custom constraints
        async with migration_engine.begin() as conn:
            result = await conn.execute(
                text(f"SELECT COUNT(*) FROM {isolated_migration_schema}.users WHERE email IS NULL")
            )
            null_count = result.scalar()
            assert null_count == 0, "Found users with NULL email"
```

### Validate specific migration

```python
async def test_migration_abc123_creates_index(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Verify migration abc123 creates expected index."""
    # Upgrade to specific revision
    await run_alembic_upgrade(alembic_config, migration_engine, "abc123")

    # Verify index exists
    async with migration_engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = :schema AND indexname = 'idx_users_email'
                """
            ),
            {"schema": isolated_migration_schema},
        )
        index_name = result.scalar()
        assert index_name == "idx_users_email", "Index not created"
```

## Testcontainers integration

### Basic usage

```python
from alembic_gauntlet.contrib.testcontainers import TestcontainersDatabaseMixin


class TestWithContainer(TestcontainersDatabaseMixin, MigrationTestBase):
    """Automatic PostgreSQL container management."""

    @pytest.fixture
    def orm_metadata(self):
        from myapp.db import Base
        return Base.metadata
```

That's it! The container is automatically:
- Started before tests
- Configured with correct credentials
- Cleaned up after tests

### Custom container configuration

```python
from testcontainers.postgres import PostgresContainer


class TestWithCustomContainer(MigrationTestBase):
    @pytest.fixture(scope="session")
    def postgres_container(self):
        """Custom PostgreSQL container."""
        container = PostgresContainer(
            image="postgres:16",
            username="testuser",
            password="testpass",
            dbname="testdb",
        )
        container.with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF-8")
        container.start()
        yield container
        container.stop()

    @pytest.fixture(scope="session")
    def migration_db_url(self, postgres_container) -> str:
        return postgres_container.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+asyncpg"
        )

    @pytest.fixture
    def orm_metadata(self):
        from myapp.db import Base
        return Base.metadata
```

### Multiple database versions

```python
@pytest.fixture(scope="session", params=["postgres:14", "postgres:15", "postgres:16"])
def postgres_container(self, request):
    """Test against multiple PostgreSQL versions."""
    container = PostgresContainer(image=request.param)
    container.start()
    yield container
    container.stop()
```

## Working with partitioned tables

Partitioned tables often need special handling.

### Ignore partitions in diff

```python
from typing import ClassVar


class TestWithPartitions(MigrationTestBase):
    migration_diff_ignore_tables: ClassVar[list[str]] = [
        "alembic_version",
        "events_default",      # Default partition
        "events_2024_01",      # Monthly partitions
        "events_2024_02",
        "events_2024_03",
    ]
```

### Pattern-based ignore

```python
from alembic_gauntlet.utils.diff import is_ignored_diff_item


def custom_is_ignored(diff_item: tuple, ignore_tables: frozenset[str]) -> bool:
    """Ignore all tables matching pattern."""
    if len(diff_item) < 2:
        return False
    
    operation, subject = diff_item[0], diff_item[1]
    
    # Get table name
    if hasattr(subject, "name"):
        table_name = subject.name
    elif hasattr(subject, "table") and hasattr(subject.table, "name"):
        table_name = subject.table.name
    else:
        return False
    
    # Ignore partitions matching pattern
    if table_name and table_name.startswith("events_202"):
        return True
    
    return is_ignored_diff_item(diff_item, ignore_tables)
```

## Custom naming conventions

### Per-table conventions

```python
from alembic_gauntlet.utils.naming import fetch_table_naming_results


async def test_custom_naming_rules(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Validate naming with custom per-table rules."""
    await run_alembic_upgrade(alembic_config, migration_engine, "head")

    async with migration_engine.begin() as conn:
        results = await fetch_table_naming_results(conn, isolated_migration_schema)

    # Custom validation
    for table_name, info in results.items():
        if table_name == "users":
            # Users table must have email index
            assert "idx_users_email" in info["indexes"], "Missing email index"
        
        if table_name.startswith("audit_"):
            # Audit tables must have created_at index
            has_created_at_idx = any(
                "created_at" in idx for idx in info["indexes"]
            )
            assert has_created_at_idx, f"Missing created_at index on {table_name}"
```

## Migration data validation

### Validate data transformations

```python
async def test_migration_preserves_data(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Ensure migration doesn't lose data."""
    # Insert test data at specific revision
    await run_alembic_upgrade(alembic_config, migration_engine, "abc123")
    
    async with migration_engine.begin() as conn:
        await conn.execute(
            text(f"INSERT INTO {isolated_migration_schema}.users (id, email) VALUES (1, 'test@example.com')")
        )
        await conn.commit()

    # Upgrade to next revision
    await run_alembic_upgrade(alembic_config, migration_engine, "def456")

    # Verify data still exists
    async with migration_engine.begin() as conn:
        result = await conn.execute(
            text(f"SELECT email FROM {isolated_migration_schema}.users WHERE id = 1")
        )
        email = result.scalar()
        assert email == "test@example.com", "Data lost during migration"
```

### Test data migration scripts

```python
async def test_backfill_migration(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Test data backfill in migration."""
    # Set up data before migration
    await run_alembic_upgrade(alembic_config, migration_engine, "abc123")
    
    async with migration_engine.begin() as conn:
        # Insert records without new column
        await conn.execute(
            text(f"INSERT INTO {isolated_migration_schema}.users (id, email) VALUES (1, 'user1@example.com'), (2, 'user2@example.com')")
        )
        await conn.commit()

    # Run migration with backfill
    await run_alembic_upgrade(alembic_config, migration_engine, "def456")

    # Verify backfill worked
    async with migration_engine.begin() as conn:
        result = await conn.execute(
            text(f"SELECT id, status FROM {isolated_migration_schema}.users ORDER BY id")
        )
        rows = result.fetchall()
        assert all(row.status == "active" for row in rows), "Backfill failed"
```

## Performance testing

### Measure migration duration

```python
import time


async def test_migration_performance(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Ensure migrations complete within time budget."""
    start = time.time()
    await run_alembic_upgrade(alembic_config, migration_engine, "head")
    duration = time.time() - start

    # Fail if migration takes too long
    assert duration < 30.0, f"Migration took {duration:.2f}s (max 30s)"
```

### Benchmark large data migrations

```python
async def test_large_data_migration_performance(
    self,
    isolated_migration_schema: str,
    migration_engine: AsyncEngine,
    alembic_config: Config,
) -> None:
    """Test migration performance with large dataset."""
    # Set up large dataset
    await run_alembic_upgrade(alembic_config, migration_engine, "abc123")
    
    async with migration_engine.begin() as conn:
        # Insert 1M records
        await conn.execute(
            text(
                f"""
                INSERT INTO {isolated_migration_schema}.users (email)
                SELECT 'user' || generate_series(1, 1000000) || '@example.com'
                """
            )
        )
        await conn.commit()

    # Time the migration
    start = time.time()
    await run_alembic_upgrade(alembic_config, migration_engine, "def456")
    duration = time.time() - start

    print(f"Migration with 1M rows took {duration:.2f}s")
    assert duration < 60.0, "Migration too slow for production"
```

## CI/CD integration

### GitHub Actions example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio
      
      - name: Run migration tests
        env:
          TEST_DB_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
        run: pytest tests/migrations/ -v
```

### GitLab CI example

```yaml
# .gitlab-ci.yml
test:migrations:
  image: python:3.12
  services:
    - postgres:16
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    TEST_DB_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/test_db
  script:
    - pip install -e .
    - pip install pytest pytest-asyncio
    - pytest tests/migrations/ -v
```

## Next steps

- [API reference](../reference/index.md) — complete API documentation
- [Quick start](quickstart.md) — basic setup guide
- [Configuration](configuration.md) — all configuration options
