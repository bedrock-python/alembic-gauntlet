"""Optional ``migration_db_url`` fixture powered by testcontainers.

Import this fixture in your ``conftest.py`` to get a fully managed PostgreSQL
container without any external setup::

    # tests/conftest.py
    from alembic_gauntlet.contrib.testcontainers import migration_db_url  # noqa: F401

The fixture has ``session`` scope, so the container starts once per test session.
Override ``migration_db_url`` in your own conftest to use a different database.

Requires the optional extra::

    pip install "alembic-gauntlet[testcontainers]"
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from testcontainers.community.postgres import PostgresContainer


def _import_postgres_container() -> type[PostgresContainer]:
    try:
        from testcontainers.community.postgres import PostgresContainer  # noqa: PLC0415
    except ImportError:
        # testcontainers < 4.15.0 has no ``community`` package; 4.15.0 deprecates this path.
        try:
            from testcontainers.postgres import PostgresContainer  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                'testcontainers is not installed. Install it with: pip install "alembic-gauntlet[testcontainers]"'
            ) from exc
    return PostgresContainer


@pytest.fixture(scope="session")
def migration_db_url() -> Generator[str, None, None]:
    """Start a PostgreSQL 17 container and yield its async DSN.

    The container is stopped automatically at the end of the test session.

    Raises:
        ImportError: If ``testcontainers`` is not installed.
    """
    container_class = _import_postgres_container()
    with container_class("postgres:17-alpine") as pg:
        dsn = pg.get_connection_url()
        # testcontainers returns a psycopg2 URL; swap the driver for asyncpg.
        yield dsn.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
