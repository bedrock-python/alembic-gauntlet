# alembic-gauntlet

Testing toolkit for Alembic migrations — run your migrations through the gauntlet

[![PyPI](https://img.shields.io/pypi/v/alembic-gauntlet?color=blue)](https://pypi.org/project/alembic-gauntlet/)
[![Python](https://img.shields.io/pypi/pyversions/alembic-gauntlet)](https://pypi.org/project/alembic-gauntlet/)
[![License](https://img.shields.io/github/license/bedrock-python/alembic-gauntlet)](LICENSE)
[![CI](https://github.com/bedrock-python/alembic-gauntlet/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/bedrock-python/alembic-gauntlet/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bedrock-python/alembic-gauntlet/graph/badge.svg)](https://codecov.io/gh/bedrock-python/alembic-gauntlet)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://bedrock-python.github.io/alembic-gauntlet/)

## Installation

```bash
pip install alembic-gauntlet
```

**Requirements:** Python 3.11+

## Quick start

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

## Documentation

Full documentation at [bedrock-python.github.io/alembic-gauntlet](https://bedrock-python.github.io/alembic-gauntlet/).

## License

Apache 2.0 — see [LICENSE](LICENSE).
