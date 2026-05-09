# alembic-gauntlet

**Testing toolkit for Alembic migrations — run your migrations through the gauntlet**

`alembic-gauntlet` provides comprehensive testing for your Alembic database migrations with minimal setup. Get stairway tests, schema consistency checks, naming convention validation, and more — all in one base class.

## Features

✅ **Stairway tests** — verify every migration can upgrade and downgrade  
✅ **Schema consistency** — ensure migrations match your ORM models  
✅ **Naming conventions** — validate index and foreign key names  
✅ **Branch detection** — catch unmerged migration branches  
✅ **Isolated schemas** — parallel-safe test execution  
✅ **Testcontainers support** — optional PostgreSQL container management

## Installation

```bash
pip install alembic-gauntlet
```

**Optional dependencies:**
```bash
pip install "alembic-gauntlet[testcontainers]"  # Auto-managed PostgreSQL container
```

**Requirements:** Python 3.11+, PostgreSQL

## Quick example

```python
import pytest
from alembic_gauntlet import MigrationTestBase
from sqlalchemy import MetaData
from myapp.db import Base


@pytest.mark.integration
class TestMyMigrations(MigrationTestBase):
    """All five tests inherited automatically."""

    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata

    @pytest.fixture(scope="session")
    def migration_db_url(self) -> str:
        return "postgresql+asyncpg://user:pass@localhost/testdb"
```

That's it! You now have:

- `test_stairway_upgrade_downgrade` — each migration forward and back
- `test_migrations_up_to_date` — schema matches ORM models
- `test_single_head_revision` — no unmerged branches
- `test_downgrade_all_the_way` — full downgrade to base
- `test_naming_conventions` — indexes and FKs follow conventions

## Next steps

- [Quick start guide](guide/quickstart.md) — step-by-step setup
- [Configuration](guide/configuration.md) — customize test behavior
- [Advanced usage](guide/advanced.md) — mixins, testcontainers, custom validations
- [API reference](reference/index.md) — complete API documentation

## Why alembic-gauntlet?

Alembic migrations are powerful but error-prone. Common issues:

- ❌ Migration works forward but breaks on downgrade
- ❌ Forgot to run `alembic revision --autogenerate` after model changes
- ❌ Unmerged migration branches cause conflicts
- ❌ Inconsistent naming breaks your team's conventions

`alembic-gauntlet` catches all of these automatically. Write your migrations, inherit from `MigrationTestBase`, and let the gauntlet do its job.

## License

Apache 2.0 — see [LICENSE](https://github.com/bedrock-python/alembic-gauntlet/blob/master/LICENSE).
