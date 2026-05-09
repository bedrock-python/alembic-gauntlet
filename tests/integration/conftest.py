"""Integration test fixtures.

Imports the testcontainers-based ``migration_db_url`` fixture so all integration
tests get a PostgreSQL container automatically.
"""

from alembic_gauntlet.contrib.testcontainers import migration_db_url  # noqa: F401
