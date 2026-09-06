# Quick start

This guide will walk you through setting up `alembic-gauntlet` for your project.

## Prerequisites

- Python 3.10+
- PostgreSQL database
- An async PostgreSQL driver (`asyncpg`)
- Existing Alembic migrations
- SQLAlchemy ORM models

## Installation

Install `alembic-gauntlet` with the `asyncio` extra:

```bash
pip install "alembic-gauntlet[asyncio]"
```

The extra pulls in `pytest-asyncio`. The tests you inherit and the fixtures that feed them
are plain `async def`, so without it your suite errors out — see
[Configure pytest](#2-configure-pytest) for the one setting it needs.

For automatic PostgreSQL container management with Testcontainers:

```bash
pip install "alembic-gauntlet[testcontainers]"
```

## Basic setup

### 1. Create a test file

Create a new file in your tests directory (e.g., `tests/migrations/test_migrations.py`):

```python
import pytest
from alembic_gauntlet import MigrationTestBase
from sqlalchemy import MetaData
from myapp.db import Base  # Your SQLAlchemy declarative base


@pytest.mark.integration
class TestMyMigrations(MigrationTestBase):
    """Migration tests for myapp."""

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        """Provide ORM metadata for schema consistency checks."""
        return Base.metadata

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        """Provide database URL for migrations."""
        return "postgresql+asyncpg://user:pass@localhost:5432/testdb"
```

That's it! You now have 5 tests automatically:

- `test_stairway_upgrade_downgrade` — each migration forward and back
- `test_migrations_up_to_date` — schema matches ORM models
- `test_single_head_revision` — no unmerged branches
- `test_downgrade_all_the_way` — full downgrade to base
- `test_naming_conventions` — indexes and FKs follow conventions

### 2. Configure pytest

Turn on pytest-asyncio's auto mode and add the integration marker:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "integration: marks tests as integration tests (require database)",
]
```

Or in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
markers =
    integration: marks tests as integration tests (require database)
```

`asyncio_mode` is a requirement, not a preference. The inherited tests and the
`migration_engine` and `isolated_migration_schema` fixtures are declared with plain
`@pytest.fixture` and no `asyncio` marker; under the default strict mode the tests fail
with *async def functions are not natively supported* and the fixtures arrive unawaited.

### 3. Run the tests

Run all migration tests:

```bash
pytest tests/migrations/ -v
```

Or run only integration tests:

```bash
pytest -m integration -v
```

## Expected output

When tests pass, you'll see:

```
tests/migrations/test_migrations.py::TestMyMigrations::test_stairway_upgrade_downgrade PASSED
tests/migrations/test_migrations.py::TestMyMigrations::test_migrations_up_to_date PASSED
tests/migrations/test_migrations.py::TestMyMigrations::test_single_head_revision PASSED
tests/migrations/test_migrations.py::TestMyMigrations::test_downgrade_all_the_way PASSED
tests/migrations/test_migrations.py::TestMyMigrations::test_naming_conventions PASSED
```

## What each test does

### test_stairway_upgrade_downgrade

**Stairway test** — ensures every migration can upgrade and downgrade without errors.

This test:
1. Gets all revisions from Alembic
2. For each revision:
   - Upgrades to that revision
   - Downgrades one step
   - Upgrades again

**Catches**:
- Migrations that work forward but fail on downgrade
- Missing downgrade operations
- Non-idempotent migrations

### test_migrations_up_to_date

**Schema consistency check** — ensures your migrations match your ORM models.

This test:
1. Runs all migrations to HEAD
2. Compares database schema with ORM metadata
3. Reports any differences

**Catches**:
- Forgot to run `alembic revision --autogenerate`
- Model changes not reflected in migrations
- Drift between database and code

### test_single_head_revision

**Branch detection** — ensures no unmerged migration branches.

This test:
1. Checks Alembic revision tree
2. Ensures only one HEAD revision exists

**Catches**:
- Multiple developers creating migrations on different branches
- Merge conflicts in migration history
- Unmerged feature branches

### test_downgrade_all_the_way

**Full downgrade test** — ensures complete rollback works.

This test:
1. Upgrades to HEAD
2. Downgrades all the way to base
3. Verifies no errors

**Catches**:
- Incomplete downgrade operations
- Missing foreign key drops
- Orphaned database objects

### test_naming_conventions

**Naming convention validation** — ensures consistent naming.

This test:
1. Runs migrations to HEAD
2. Inspects all indexes and foreign keys
3. Validates names match conventions

**Catches**:
- Inconsistent index naming (`idx_` vs `_idx`)
- Foreign keys without proper suffix (`_fkey`)
- Unconventional constraint names

**Default conventions**:

| Object | Allowed prefixes | Allowed suffixes |
|--------|-----------------|-----------------|
| Index | `idx_`, `uq_` | `_idx`, `_pkey`, `_key` |
| Foreign key | `fk_` | `_fkey` |
| CHECK constraint | `chk_` | — |
| UNIQUE constraint | `uq_` | — |
| PRIMARY KEY | `pk_` | `_pkey` |

If your `MetaData` carries a `naming_convention`, the rules are derived
automatically — no class attributes needed. See
[Configuration](configuration.md#auto-deriving-rules-from-metadatanaming_convention)
for details.

## Using Testcontainers

For automatic PostgreSQL container management, install the `testcontainers` extra and
import the `migration_db_url` fixture it ships into your `conftest.py`:

```python
# tests/conftest.py
from alembic_gauntlet.contrib.testcontainers import migration_db_url  # noqa: F401
```

Your test class then only needs `orm_metadata` — the fixture supplies the database:

```python
import pytest
from alembic_gauntlet import MigrationTestBase


@pytest.mark.integration
class TestMyMigrations(MigrationTestBase):
    """Migrations with automatic PostgreSQL container."""

    @pytest.fixture
    def orm_metadata(self):
        from myapp.db import Base
        return Base.metadata
```

The fixture is session-scoped, so one `postgres:17-alpine` container:

- starts once per test session
- yields its connection URL rewritten to `postgresql+asyncpg://`
- is stopped when the session ends

No manual database setup required. Override `migration_db_url` in your own conftest to
point at a different database.

## Troubleshooting

### Test fails: "Schema differences detected"

Your migrations are out of sync with ORM models. Run:

```bash
alembic revision --autogenerate -m "sync models"
```

### Test fails: "Multiple head revisions"

You have unmerged migration branches. Merge them:

```bash
alembic merge -m "merge heads" head_1 head_2
```

### Test fails on downgrade

Your migration is missing downgrade operations. Edit the migration file and add proper `downgrade()` logic.

### Connection errors

Verify database URL and credentials:

```python
@pytest.fixture(scope="session")
def migration_db_url(self) -> str:
    # Check this URL is correct
    return "postgresql+asyncpg://user:pass@localhost:5432/testdb"
```

## Next steps

- [Configuration](configuration.md) — customize test behavior
- [Configuring env.py](env-py.md) — connect alembic-gauntlet to your migrations
- [Advanced usage](advanced.md) — mixins, custom validations
- [API reference](../reference/index.md) — complete API docs
