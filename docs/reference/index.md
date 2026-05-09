# API Reference

Auto-generated API documentation from source code using [mkdocstrings](https://mkdocstrings.github.io/).

## Testing

### MigrationTestBase

::: alembic_gauntlet.testing.MigrationTestBase
    options:
      heading_level: 4
      show_source: false

### MigrationSchemaMixin

::: alembic_gauntlet.testing.MigrationSchemaMixin
    options:
      heading_level: 4
      show_source: false

### MigrationConsistencyMixin

::: alembic_gauntlet.testing.MigrationConsistencyMixin
    options:
      heading_level: 4
      show_source: false

### MigrationNamingMixin

::: alembic_gauntlet.testing.MigrationNamingMixin
    options:
      heading_level: 4
      show_source: false

## Utilities

### Migration utilities

::: alembic_gauntlet.utils.migrations
    options:
      heading_level: 4
      members:
        - run_alembic_upgrade
        - run_alembic_downgrade
        - get_current_revision
        - get_all_revisions
        - create_isolated_migration_schema

### Schema validation

::: alembic_gauntlet.utils.validation
    options:
      heading_level: 4
      members:
        - validate_schema_name

### Diff utilities

::: alembic_gauntlet.utils.diff
    options:
      heading_level: 4
      members:
        - is_ignored_diff_item
        - DEFAULT_IGNORE_TABLES

### Naming utilities

::: alembic_gauntlet.utils.naming
    options:
      heading_level: 4
      members:
        - fetch_table_naming_results
        - validate_naming_results

## Fixtures

### Core fixtures

::: alembic_gauntlet.fixtures
    options:
      heading_level: 4
      members:
        - alembic_config
        - migration_engine

## Exceptions

::: alembic_gauntlet.exceptions
    options:
      heading_level: 4
      show_source: false

## Contrib

### Testcontainers

::: alembic_gauntlet.contrib.testcontainers
    options:
      heading_level: 4
      show_source: false

## Type aliases

### MigrationDiff

::: alembic_gauntlet.testing.MigrationDiff
    options:
      heading_level: 4
      show_source: true
