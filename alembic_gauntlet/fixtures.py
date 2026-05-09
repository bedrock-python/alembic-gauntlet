"""Standard pytest fixtures for Alembic migration testing."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture
def alembic_config() -> Config:
    """Create an Alembic :class:`~alembic.config.Config` from ``alembic.ini``.

    Override this fixture in your test class to point to a different ``alembic.ini``::

        @pytest.fixture
        def alembic_config(self) -> Config:
            from pathlib import Path
            from alembic.config import Config
            ini = Path(__file__).parent.parent / "alembic.ini"
            return Config(str(ini))
    """
    return _create_alembic_config()


def _create_alembic_config(ini_path: Path = Path("alembic.ini")) -> Config:
    if not ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {ini_path.absolute()}. "
            "Run tests from the service root directory or override the 'alembic_config' fixture."
        )
    config = Config(str(ini_path))
    if not config.get_main_option("script_location"):
        config.set_main_option("script_location", "migrations")
    return config


@pytest.fixture
async def migration_engine(migration_db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Async engine with :class:`~sqlalchemy.pool.NullPool` for migration tests.

    NullPool prevents connection reuse between tests, which is important for
    schema isolation when running tests in parallel.

    Requires the ``migration_db_url`` fixture to be provided.
    """
    engine = create_async_engine(migration_db_url, echo=False, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()
