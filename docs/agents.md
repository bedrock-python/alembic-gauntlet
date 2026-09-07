# alembic-gauntlet for AI agents

> One page holding everything a coding assistant needs to wire alembic-gauntlet into a
> test suite and read what it reports, plus a map of where the rest of the documentation
> keeps the details it leaves out. Give an agent this page rather than the whole site.

| | |
|---|---|
| Package | `alembic-gauntlet` on PyPI, import root `alembic_gauntlet` |
| Requires | Python 3.10+, PostgreSQL, SQLAlchemy 2, Alembic 1.8+, pytest 7+ |
| Install | `pip install "alembic-gauntlet[asyncio]"` · extras: `asyncio` (pytest-asyncio), `testcontainers` |
| Also install | an async PostgreSQL driver (`asyncpg`); `pytest-asyncio` comes with the `asyncio` extra and has to run in `asyncio_mode = "auto"` |
| Entry point | `MigrationTestBase` — inherit it, supply two fixtures, get seven tests |
| Pytest plugin | `alembic_gauntlet.fixtures` is registered under `pytest11`, so `alembic_config` and `migration_engine` exist with no import and no conftest entry |
| Async / sync | everything that touches the database is a coroutine over an `AsyncEngine`; the naming, diff and validation helpers are ordinary sync functions |
| Source | <https://github.com/bedrock-python/alembic-gauntlet> |

## How to read this page

Every page of this site is also served as raw Markdown at its own URL with `.md` in place
of the trailing slash — this page is `/agents.md`, the quick start is
`/guide/quickstart.md` — so anything the map below points at can be fetched as plain text
rather than scraped out of HTML. The **Copy page** control at the top of a page does the
same thing for a human with a chat window open. The one exception is the API reference:
its Markdown is a list of instructions to a docstring renderer rather than the API, so it
carries neither the control nor a `.md` twin — read it as HTML, or read the docstrings in
the source.

Top to bottom before writing code. [Rules that hold or break the code](#rules-that-hold-or-break-the-code)
is the section correctness lives in — those are the things the library will not save you
from. Every name used below exists in this version; if you need something not listed here,
fetch the page the [documentation map](#documentation-map) points at rather than guessing
a method that sounds plausible.

## Scope

**It does** run your real Alembic history against a real PostgreSQL database, inside a
throwaway schema, as seven pytest tests you inherit: every revision up and back down one
step at a time, a full downgrade to base, an autogenerate diff of the migrated database
against your ORM metadata, a name-by-name comparison of its CHECK constraints, a
value-by-value comparison of its enum types, a single-head check, and a naming check over
every index, foreign key, check, unique and primary key constraint. The pieces underneath
— upgrade, downgrade, current revision, all revisions, an isolated schema, the two
comparisons — are public, so you can write your own checks with them.

**It does not** create the database, write your `env.py`, or run migrations anywhere but a
test. It never shells out to the `alembic` command; it drives `alembic.command` in-process
on a connection it injects. There is no sync API and no non-PostgreSQL support: schema
isolation, the reserved-word check and the constraint inspection are PostgreSQL. It seeds
no data, asserts nothing about your data, and cleans up nothing outside the schema it
created.

## Mental model

Five nouns and one contract.

* **Two fixtures are yours.** `migration_db_url` — an async DSN to a live PostgreSQL —
  and `orm_metadata` — the `MetaData` your models hang off. Everything else has a default.
* **`alembic_config`** comes from the plugin: `Config("alembic.ini")` read from the
  process working directory, with `script_location` defaulting to `migrations` when the
  ini leaves it empty. Override the fixture when your ini lives elsewhere.
* **`migration_engine`** comes from the plugin: `create_async_engine(migration_db_url,
  poolclass=NullPool)`, function-scoped, disposed after each test. `NullPool` is the point
  — no connection is reused between tests, which is what makes parallel runs safe.
* **`isolated_migration_schema`** comes from `MigrationSchemaMixin`: a fresh
  `test_mig_<8 hex chars>` schema created on its own engine, yielded to the test, then
  dropped with `CASCADE`. One schema per test.
* **The env.py contract** is the half you own. Before calling `alembic.command.upgrade` /
  `downgrade`, the runner sets `config.attributes["connection"]` (a live sync
  `Connection`, already inside `engine.begin()`) and `config.attributes["target_schema"]`
  (the isolated schema name), and pops both in a `finally`. Your `env.py` must use the
  injected connection when it is there, and must put the version table and the
  `search_path` in `target_schema`. An `env.py` that ignores them migrates the wrong
  database in the wrong schema and every test above becomes theatre. See
  [Configuring env.py](guide/env-py.md).
* **`MigrationTestBase`** is `MigrationSchemaMixin` + `MigrationConsistencyMixin` +
  `MigrationNamingMixin`. Inherit the mixins directly when you want fewer than seven tests;
  `MigrationSchemaMixin` has to be among them, because the other two request
  `isolated_migration_schema`.

## Wiring

`tests/conftest.py` — a container for the database, or your own URL:

```python
# either: a managed PostgreSQL 17 container (extra: testcontainers)
from alembic_gauntlet.contrib.testcontainers import migration_db_url  # noqa: F401

# or: your own, session-scoped
import pytest


@pytest.fixture(scope="session")
def migration_db_url() -> str:
    return "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
```

`tests/test_migrations.py`:

```python
import pytest
from alembic.config import Config
from sqlalchemy import MetaData

from alembic_gauntlet import MigrationTestBase
from myapp.db import Base


@pytest.mark.integration
class TestMigrations(MigrationTestBase):
    @pytest.fixture
    def orm_metadata(self) -> MetaData:
        return Base.metadata

    @pytest.fixture
    def alembic_config(self) -> Config:          # only when alembic.ini is not in the CWD
        config = Config("myapp/alembic.ini")
        config.set_main_option("script_location", "myapp/alembic")
        return config
```

`pyproject.toml` — the tests and fixtures are `async def` with no marker, so auto mode is
not optional:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

That is the whole integration: seven tests, named in the table below, collected from the
base class.

## The API

### Root exports — `from alembic_gauntlet import ...`

| Name | Kind | Signature and result |
|---|---|---|
| `MigrationTestBase` | class | the base class carrying all seven tests |
| `run_alembic_upgrade` | coroutine | `(engine, alembic_config, target_schema="public", revision="head") -> None` |
| `run_alembic_downgrade` | coroutine | `(engine, alembic_config, target_schema="public", revision="base") -> None` |
| `get_current_revision` | coroutine | `(engine, target_schema="public") -> str | None` — `None` means base |
| `get_all_revisions` | **sync** | `(alembic_config) -> list[str]`, base → head |
| `create_isolated_migration_schema` | **async generator** | `(migration_db_url) -> AsyncGenerator[str, None]`, one schema, dropped on close |
| `SchemaValidationError` and four subclasses | exceptions | see [Errors](#errors) |

`engine` is the first positional argument of every runner, and `alembic_config` the
second. Both `target_schema` and `revision` are ordinary positional-or-keyword arguments;
pass them by name.

### `alembic_gauntlet.testing`

| Name | What it carries |
|---|---|
| `MigrationTestBase` | the three mixins, plus `migration_diff_ignore_tables: ClassVar[list[str]] = []` |
| `MigrationSchemaMixin` | the `isolated_migration_schema` fixture, and nothing else |
| `MigrationConsistencyMixin` | `test_stairway_upgrade_downgrade`, `test_migrations_up_to_date`, `test_check_constraints_match`, `test_enum_values_match`, `test_single_head_revision`, `test_downgrade_all_the_way`, and `migration_diff_compare_server_default: ClassVar[bool] = False` |
| `MigrationNamingMixin` | `test_naming_conventions`, the ten `allowed_*` class attributes and the rule resolution |
| `MigrationDiff` | type alias `list[tuple[MigrateOperation, ...]]` — what `compare_metadata()` returns |

### Fixtures

| Fixture | Provided by | Scope | Value |
|---|---|---|---|
| `migration_db_url` | **you** | yours, session is usual | async DSN to a live PostgreSQL |
| `orm_metadata` | **you** | yours | `MetaData` of your models |
| `migration_db_url` | `alembic_gauntlet.contrib.testcontainers`, imported into a conftest | session | starts `postgres:17-alpine`, yields its DSN rewritten to `postgresql+asyncpg://` |
| `alembic_config` | plugin (`alembic_gauntlet.fixtures`) | function | `Config("alembic.ini")` from the CWD; `FileNotFoundError` if it is not there |
| `migration_engine` | plugin | function | `AsyncEngine` with `NullPool`, disposed afterwards |
| `isolated_migration_schema` | `MigrationSchemaMixin` | function | `test_mig_<8 hex chars>`, dropped with `CASCADE` |

### The seven tests

| Test | Requests | Asserts |
|---|---|---|
| `test_stairway_upgrade_downgrade` | config, engine, schema | for each revision base → head: upgrade to it, current revision matches, downgrade one step, current revision matches the step below, upgrade back |
| `test_migrations_up_to_date` | config, engine, schema, `orm_metadata` | after a full upgrade, `compare_metadata()` against your metadata is empty once ignored tables are filtered out; server defaults take part only when `migration_diff_compare_server_default` is on |
| `test_check_constraints_match` | config, engine, schema, `orm_metadata` | after a full upgrade, every named CHECK constraint in your metadata exists under the name the DDL would give it, and a table whose model names all of its check constraints has no others |
| `test_enum_values_match` | config, engine, schema, `orm_metadata` | after a full upgrade, every native, named `Enum` column's values equal the database type's labels, in order |
| `test_single_head_revision` | config | `ScriptDirectory.get_revisions("heads")` has exactly one entry |
| `test_downgrade_all_the_way` | config, engine, schema | upgrade to head, then step down through every revision to base; the final current revision is `None` |
| `test_naming_conventions` | config, engine, schema, `orm_metadata` | after a full upgrade, every index, foreign key, check, unique and primary key name in the schema matches the resolved rules |

The stairway and downgrade tests call `pytest.skip("No migrations found.")` when the
history is empty. Failures are plain `assert` failures with the offending name in the
message — there is no custom exception for a failed check.

### Class attributes

| Attribute | Default | Effect |
|---|---|---|
| `migration_diff_ignore_tables` | `[]` | added to `DEFAULT_IGNORE_TABLES` (`{"alembic_version"}`) for the diff test, and drops those tables from the check constraint, enum and naming tests |
| `migration_diff_compare_server_default` | `False` | passes `compare_server_default` to Alembic in the diff test; rule 9 below says what agrees and what is reported |
| `allowed_index_prefixes` | `["idx_", "uq_"]` | index names |
| `allowed_index_suffixes` | `["_idx", "_pkey", "_key"]` | index names, one optional trailing digit tolerated (`users_pkey1`) |
| `allowed_fk_prefixes` / `allowed_fk_suffixes` | `["fk_"]` / `["_fkey"]` | foreign key constraint names |
| `allowed_check_prefixes` / `allowed_check_suffixes` | `["chk_"]` / `[]` | check constraint names |
| `allowed_uq_prefixes` / `allowed_uq_suffixes` | `["uq_"]` / `[]` | unique constraint names |
| `allowed_pk_prefixes` / `allowed_pk_suffixes` | `["pk_"]` / `["_pkey"]` | primary key constraint names |

Rules resolve in three layers, last wins: the defaults above, then whatever
`rules_from_metadata(orm_metadata)` extracts from `orm_metadata.naming_convention`, then
attributes set explicitly on your class. Layer two takes the literal text before the first
`%(` as a prefix and the literal text after the last `)s` as a suffix, replaces a category
only when it found one, and ignores SQLAlchemy's own built-in convention
(`{"ix": "ix_%(column_0_label)s"}` alone). A `uq` template also joins the index rules,
because PostgreSQL implements a unique constraint as an index.

### Helpers below the fixtures

| Import | Signature | Use |
|---|---|---|
| `alembic_gauntlet.utils.naming.fetch_table_naming_results` | `(sync_conn, schema) -> dict[str, TableNamingResults]` | **sync**; `alembic_version` always excluded |
| `alembic_gauntlet.utils.naming.validate_naming_results` | `(results, allowed_index_prefixes, …, allowed_pk_suffixes) -> None` | asserts; every `allowed_*` argument is required |
| `alembic_gauntlet.utils.diff.is_ignored_diff_item` | `(diff_item, ignore_tables) -> bool` | filters `remove_table` and `remove_index` items only |
| `alembic_gauntlet.utils.diff.DEFAULT_IGNORE_TABLES` | `frozenset({"alembic_version"})` | the baseline of the diff filter |
| `alembic_gauntlet.utils.diff.compare_check_constraints` | `(sync_conn, metadata, schema, ignore_tables=frozenset()) -> list[str]` | **sync**; one line per CHECK constraint that differs by name, empty when in sync |
| `alembic_gauntlet.utils.diff.compare_enums` | `(sync_conn, metadata, schema, ignore_tables=frozenset()) -> list[str]` | **sync**; one line per enum type whose values differ, in order, empty when in sync |
| `alembic_gauntlet.utils.validation.validate_schema_name` | `(name, connection=None) -> None` | format, 63-byte length, and reserved words when a connection is given |
| `alembic_gauntlet.utils.validation.get_pg_reserved_words` | `(connection) -> set[str]` | reads `pg_get_keywords()` |
| `alembic_gauntlet.utils.convention.rules_from_metadata` | `(metadata) -> NamingConventionRules` | the layer-two extraction, as a dataclass of ten lists |

`TableNamingResults` and `ForeignKeyInfo` are `TypedDict`s in `alembic_gauntlet.utils.naming`;
a result maps a table name to `indexes`, `fks`, `check_constraints`, `unique_constraints`
and `pk_constraint`.

## Rules that hold or break the code

1. **`asyncio_mode = "auto"`.** The inherited tests and the library's fixtures are
   `async def` declared with plain `@pytest.fixture` and no `asyncio` marker. Under
   pytest-asyncio's default strict mode the tests fail with *async def functions are not
   natively supported* and the fixtures arrive as unawaited generators. Auto mode is a
   requirement, not a preference, and pytest-asyncio is not a hard dependency of this
   package — take it from the `asyncio` extra or install it yourself.
2. **The DSN must be async.** `create_async_engine` is called on `migration_db_url`
   verbatim, so `postgresql+asyncpg://…` (or another async driver) and the driver
   installed. A bare `postgresql://…` selects psycopg2 and never reaches the database:
   `InvalidRequestError: The asyncio extension requires an async driver` where psycopg2 is
   installed, `ModuleNotFoundError` where it is not.
3. **Your `env.py` decides whether any of this is real.** It must run on
   `config.attributes["connection"]` when that key is present, and must pass
   `version_table_schema=target_schema` and `SET LOCAL search_path` to
   `config.attributes["target_schema"]`. Ignore either and the tests pass while migrating
   `public` on a connection nobody rolls back. Use `SET LOCAL`, never plain `SET` — plain
   `SET` outlives the transaction and follows the connection back into the pool.
4. **Migrations run inside one transaction.** The runner opens `engine.begin()` and hands
   `alembic.command` that connection, so anything that cannot run in a transaction block —
   `CREATE INDEX CONCURRENTLY`, `ALTER TYPE … ADD VALUE` on older servers — fails here
   even though it works in production.
5. **`alembic.ini` is read from the process working directory.** The default fixture is
   `Config("alembic.ini")` and raises `FileNotFoundError` with the absolute path when it is
   missing. Run pytest from the service root, or override `alembic_config`.
6. **The stairway test assumes a linear history.** It steps to `revisions[i - 1]` in
   `walk_revisions()` order; a branched history makes those steps meaningless, which is
   what `test_single_head_revision` is there to catch first.
7. **The isolated schema is dropped with `CASCADE`.** Everything a migration created
   inside it is gone at the end of the test — and nothing it created outside it is cleaned
   up at all.
8. **`migration_diff_ignore_tables` only silences removals in the diff test.**
   `is_ignored_diff_item` recognises `remove_table` and `remove_index`, meaning tables in
   the database that your models do not know about. A table your models declare and the
   migrations never created is always reported, whatever you list. The check constraint,
   enum and naming tests skip the listed tables outright.
9. **Server defaults are compared only on request.** `compare_metadata()` skips them
   unless `compare_server_default` is set, and the diff test passes
   `migration_diff_compare_server_default`, which is `False`. With it on, Alembic's
   PostgreSQL comparison compares the two texts and, when they differ, asks the server
   whether the expressions are equal: `text("true")`, `sa.true()` and `"true"` all agree
   with a column defaulted to `true`, `func.now()` agrees with `now()` and
   `CURRENT_TIMESTAMP`, `"0"` with `0`, `text("'{}'")` with `'{}'::jsonb`, and
   `gen_random_uuid()` with itself. Reported: a different value, two different volatile
   functions (`clock_timestamp()` against `now()`), and a default present on one side only
   — a Python-side `default=` in the model is not a server default. A serial or identity
   primary key is never compared.
10. **CHECK constraints are compared by name, and only named ones.**
    `test_check_constraints_match` resolves each metadata constraint to the name the DDL
    would give it — the convention applied, a deferred `Boolean(create_constraint=True)`
    name filled in, a name over 63 characters truncated — and compares that with
    `get_check_constraints`. Expressions are never compared; PostgreSQL rewrites
    `amount > 0` as `(amount > (0)::numeric)`. An unnamed metadata constraint is skipped,
    and on its table the test also stops reporting database constraints the models lack,
    because PostgreSQL gave the unnamed one a name of its own. Name every check constraint;
    a `ck` template with `%(constraint_name)s` enforces that. Alembic's own name-based
    detection is a plugin that was on by default in 1.19.0 and 1.19.1 and is opt-in from
    1.19.2; this test does not use it, and on those two versions the diff test reports
    named CHECK constraints as well.
11. **Enum values are compared in order, per type the models use.**
    `test_enum_values_match` reads `get_enums()` and compares the labels with `Enum.enums`
    as lists for every native, named `Enum` column, looking in `Enum.schema` when set and
    in the isolated schema otherwise. A type nothing references, a non-native enum and an
    unnamed one are not compared. A migration that adds a value with `ALTER TYPE … ADD
    VALUE` has to put it where the model has it.
12. **A name passes on a prefix *or* a suffix.** The checks are not per-object-type
   exclusive and not anchored to your convention: `users_pkey` passes the primary key rule
   on `_pkey` even when you set `allowed_pk_prefixes = ["pk_"]`, because the default suffix
   is still in the resolved set. Empty both lists for a category and nothing can pass it.
13. **Layer two replaces, layer three overrides, and the walk stops at the mixin.** An
    explicit `allowed_*` attribute counts when it is set on your class or an intermediate
    base; the MRO walk breaks at `MigrationNamingMixin`, so its own sentinel values never
    win. A convention template with no literal part — `"%(table_name)s_%(column_0_name)s"` —
    contributes nothing and leaves the defaults in place.
14. **PostgreSQL only.** Isolated schemas, `pg_get_keywords()`, `DROP SCHEMA … CASCADE`
    and the constraint inspection are PostgreSQL. There is no SQLite or MySQL path, and a
    `cockroachdb+asyncpg` URL is not a supported target.
15. **Mixin fixtures are class fixtures.** `isolated_migration_schema` is defined on
    `MigrationSchemaMixin`, so it exists only inside a class that inherits it. A module-level
    test function cannot request it; call `create_isolated_migration_schema` instead.
16. **`create_isolated_migration_schema` is an async generator, not a context manager.**
    Drive it with `async for`, or wrap it in your own fixture; it has no `__aenter__`, so
    `async with` fails before the schema is ever created.
17. **Keep `NullPool` if you replace `migration_engine`.** Function scope plus `NullPool`
    is what keeps a schema-scoped `search_path` from leaking into the next test and what
    makes `pytest -n auto` safe.
18. **Schema names are validated before they reach SQL.** `validate_schema_name` runs on
    every `target_schema` the runners are given, and rejects anything that is not a plain
    identifier, is longer than 63 characters, or is a PostgreSQL reserved word. Do not
    build schema names from unvalidated input and interpolate them yourself.

## Common mistakes

```python
# WRONG — a mixin that does not exist in this package
from alembic_gauntlet.contrib.testcontainers import TestcontainersDatabaseMixin

class TestMigrations(TestcontainersDatabaseMixin, MigrationTestBase): ...

# RIGHT — contrib ships one fixture; import it into a conftest
# tests/conftest.py
from alembic_gauntlet.contrib.testcontainers import migration_db_url  # noqa: F401
```

```python
# WRONG — config first, and a string where the schema goes
await run_alembic_upgrade(alembic_config, migration_engine, "head")

# RIGHT — engine first, and the schema named
await run_alembic_upgrade(
    migration_engine, alembic_config, target_schema=isolated_migration_schema, revision="head"
)
```

```python
# WRONG — awaiting a sync function, and a sync connection helper on an async one
revisions = await get_all_revisions(alembic_config)
results = await fetch_table_naming_results(conn, schema)

# RIGHT
revisions = get_all_revisions(alembic_config)          # plain call, base -> head
async with migration_engine.connect() as conn:
    results = await conn.run_sync(lambda sc: fetch_table_naming_results(sc, schema=schema))
```

```python
# WRONG — a sync DSN, and strict-mode pytest-asyncio
def migration_db_url() -> str:
    return "postgresql://postgres:postgres@localhost:5432/test_db"

# RIGHT — an async driver, and auto mode in pyproject.toml
def migration_db_url() -> str:
    return "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
# [tool.pytest.ini_options]
# asyncio_mode = "auto"
```

```python
# WRONG — expecting the diff test to report a wrong server default
class TestMigrations(MigrationTestBase):
    ...                                   # passes with is_active DEFAULT false where the model says true

# RIGHT — turn the comparison on; CHECK constraints and enum values have their own tests
class TestMigrations(MigrationTestBase):
    migration_diff_compare_server_default = True
```

```python
# WRONG — an unnamed CHECK constraint is never compared, and a migration that spells the
# conventional name out gets the convention applied to it again (chk_orders_chk_orders_…)
__table_args__ = (CheckConstraint("amount > 0"),)
op.create_table("orders", ..., sa.CheckConstraint("amount > 0", name="chk_orders_amount_positive"))

# RIGHT — name it in the model and let the convention resolve it; op.f() keeps a name as written
__table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)   # chk_orders_amount_positive
op.create_table("orders", ..., sa.CheckConstraint("amount > 0", name=op.f("chk_orders_amount_positive")))
```

```python
# WRONG — an env.py that builds its own engine and ignores the injected one
def run_migrations_online() -> None:
    engine = create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

# RIGHT — use what the runner injected, in the schema it named
target_schema = config.attributes.get("target_schema") or os.getenv("MIGRATION_SCHEMA", "public")
connection = config.attributes.get("connection")
if connection is not None:
    do_run_migrations(connection)      # configures version_table_schema=target_schema
else:
    asyncio.run(run_migrations_online())
```

## Errors

Every exception derives from `SchemaValidationError`, and all of them come out of
`validate_schema_name`.

| Exception | Means |
|---|---|
| `SchemaValidationError` | the base — catch this to catch all four |
| `EmptySchemaNameError` | the name is `""` |
| `InvalidSchemaNameError` | the name is not `[A-Za-z_][A-Za-z0-9_]*` |
| `SchemaNameTooLongError` | longer than PostgreSQL's 63-character identifier limit |
| `ReservedWordSchemaNameError` | the name is a PostgreSQL reserved word — only raised when a `Connection` was passed, since the list is read from `pg_get_keywords()` |

Everything else surfaces as what raised it: `FileNotFoundError` from the default
`alembic_config`, `ImportError` from the testcontainers fixture without the extra,
Alembic's own `CommandError` for a bad revision, SQLAlchemy's `InvalidRequestError` for a
sync DSN, and `AssertionError` for a check that failed.

## Documentation map

Fetch a page when the task is the one named beside it.

| Page | Read it when |
|---|---|
| [Home](index.md) | the one-paragraph pitch and the shortest possible example |
| [Quick start](guide/quickstart.md) | setting the suite up step by step, and what each of the seven tests catches |
| [Configuration](guide/configuration.md) | every fixture and class attribute, with worked examples and the naming resolution order |
| [Configuring env.py](guide/env-py.md) | the `connection` / `target_schema` contract, `SET LOCAL`, advisory locks, `include_object` filtering |
| [Advanced](guide/advanced.md) | composing mixins by hand, custom checks on the isolated schema, partitioned tables, CI shapes |
| [API reference](reference/index.md) | an exact signature or docstring — HTML only, see above |
| [Changelog](changelog.md) | what changed between versions |
