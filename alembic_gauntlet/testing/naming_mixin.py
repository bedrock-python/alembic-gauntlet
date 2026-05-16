"""Naming convention tests mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from alembic_gauntlet.utils.convention import rules_from_metadata
from alembic_gauntlet.utils.migrations import run_alembic_upgrade
from alembic_gauntlet.utils.naming import fetch_table_naming_results, validate_naming_results

if TYPE_CHECKING:
    from alembic.config import Config
    from sqlalchemy import MetaData
    from sqlalchemy.ext.asyncio import AsyncEngine

_UNSET: object = object()


class MigrationNamingMixin:
    """Naming convention tests for database objects.

    Naming rules are resolved in three layers (last wins):

    1. Built-in defaults (e.g. ``allowed_fk_suffixes = ["_fkey"]``).
    2. Rules derived from ``orm_metadata.naming_convention`` (if present).
    3. Attributes explicitly set on the subclass.

    Layer 3 wins only when the attribute is explicitly overridden on the class,
    not inherited from ``MigrationNamingMixin`` itself.
    """

    allowed_index_prefixes: ClassVar[object] = _UNSET
    allowed_index_suffixes: ClassVar[object] = _UNSET
    allowed_fk_prefixes: ClassVar[object] = _UNSET
    allowed_fk_suffixes: ClassVar[object] = _UNSET
    allowed_check_prefixes: ClassVar[object] = _UNSET
    allowed_check_suffixes: ClassVar[object] = _UNSET
    allowed_uq_prefixes: ClassVar[object] = _UNSET
    allowed_uq_suffixes: ClassVar[object] = _UNSET
    allowed_pk_prefixes: ClassVar[object] = _UNSET
    allowed_pk_suffixes: ClassVar[object] = _UNSET

    _DEFAULTS: ClassVar[dict[str, list[str]]] = {
        "allowed_index_prefixes": ["idx_", "uq_"],
        "allowed_index_suffixes": ["_idx", "_pkey", "_key"],
        "allowed_fk_prefixes": ["fk_"],
        "allowed_fk_suffixes": ["_fkey"],
        "allowed_check_prefixes": ["chk_"],
        "allowed_check_suffixes": [],
        "allowed_uq_prefixes": ["uq_"],
        "allowed_uq_suffixes": [],
        "allowed_pk_prefixes": ["pk_"],
        "allowed_pk_suffixes": ["_pkey"],
    }

    def _resolve_naming_rules(self, metadata: MetaData) -> dict[str, list[str]]:
        """Merge defaults → metadata convention → explicit class overrides."""
        # Layer 1: defaults
        resolved = dict(self._DEFAULTS)

        # Layer 2: rules derived from naming_convention
        meta_rules = rules_from_metadata(metadata)
        meta_attr_map = {
            "allowed_index_prefixes": meta_rules.index_prefixes,
            "allowed_index_suffixes": meta_rules.index_suffixes,
            "allowed_fk_prefixes": meta_rules.fk_prefixes,
            "allowed_fk_suffixes": meta_rules.fk_suffixes,
            "allowed_check_prefixes": meta_rules.check_prefixes,
            "allowed_check_suffixes": meta_rules.check_suffixes,
            "allowed_uq_prefixes": meta_rules.uq_prefixes,
            "allowed_uq_suffixes": meta_rules.uq_suffixes,
            "allowed_pk_prefixes": meta_rules.pk_prefixes,
            "allowed_pk_suffixes": meta_rules.pk_suffixes,
        }
        resolved.update({attr: values for attr, values in meta_attr_map.items() if values})

        # Layer 3: explicit class-level overrides (not inherited _UNSET sentinel).
        # Walk the MRO up to (but not including) MigrationNamingMixin itself so
        # that intermediate base classes (e.g. MigrationTestBase subclasses) are
        # also considered, while the sentinel values defined here are ignored.
        for attr in self._DEFAULTS:
            for cls in type(self).__mro__:
                if cls is MigrationNamingMixin:
                    break
                if attr in cls.__dict__:
                    resolved[attr] = cls.__dict__[attr]
                    break

        return resolved

    async def test_naming_conventions(
        self,
        alembic_config: Config,
        migration_engine: AsyncEngine,
        isolated_migration_schema: str,
        orm_metadata: MetaData,
    ) -> None:
        """Verify indexes and constraints follow naming conventions after a full upgrade.

        Naming rules are auto-derived from ``orm_metadata.naming_convention`` when present,
        falling back to built-in defaults. Explicit class attributes always take priority.
        """
        await run_alembic_upgrade(
            migration_engine,
            alembic_config,
            target_schema=isolated_migration_schema,
        )

        async with migration_engine.connect() as conn:
            results = await conn.run_sync(lambda sc: fetch_table_naming_results(sc, schema=isolated_migration_schema))

        ignore_tables = frozenset(getattr(self, "migration_diff_ignore_tables", ()))
        filtered = {t: r for t, r in results.items() if t not in ignore_tables}

        rules = self._resolve_naming_rules(orm_metadata)
        validate_naming_results(filtered, **rules)
