"""Integration tests for utility functions requiring database."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic_gauntlet.utils.validation import get_pg_reserved_words


@pytest.mark.integration
async def test__get_pg_reserved_words__returns_reserved_keywords(
    migration_engine: AsyncEngine,
) -> None:
    # Arrange & Act
    async with migration_engine.connect() as conn:
        reserved = await conn.run_sync(get_pg_reserved_words)

    # Assert
    assert isinstance(reserved, set)
    assert len(reserved) > 0
    # Check some known PostgreSQL reserved words
    assert "select" in reserved
    assert "from" in reserved
    assert "where" in reserved
    assert "table" in reserved
