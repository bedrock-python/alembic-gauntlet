"""Unit tests for how MigrationNamingMixin resolves naming rules."""

from typing import ClassVar

import pytest
from sqlalchemy import MetaData

from alembic_gauntlet.testing.naming_mixin import MigrationNamingMixin


@pytest.mark.unit
def test__resolve_naming_rules__no_convention__returns_defaults() -> None:
    rules = MigrationNamingMixin()._resolve_naming_rules(MetaData())

    assert rules == MigrationNamingMixin._DEFAULTS


@pytest.mark.unit
def test__resolve_naming_rules__prefix_only_template__drops_default_suffixes() -> None:
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        }
    )

    rules = MigrationNamingMixin()._resolve_naming_rules(metadata)

    assert rules["allowed_fk_prefixes"] == ["fk_"]
    assert rules["allowed_fk_suffixes"] == []
    assert rules["allowed_pk_prefixes"] == ["pk_"]
    assert rules["allowed_pk_suffixes"] == []


@pytest.mark.unit
def test__resolve_naming_rules__suffix_only_template__drops_default_prefixes() -> None:
    metadata = MetaData(
        naming_convention={
            "ck": "%(table_name)s_%(constraint_name)s_check",
            "uq": "%(table_name)s_%(column_0_name)s_key",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
            "pk": "%(table_name)s_pkey",
        }
    )

    rules = MigrationNamingMixin()._resolve_naming_rules(metadata)

    assert rules["allowed_check_prefixes"] == []
    assert rules["allowed_check_suffixes"] == ["_check"]
    assert rules["allowed_uq_prefixes"] == []
    assert rules["allowed_uq_suffixes"] == ["_key"]
    assert rules["allowed_fk_prefixes"] == []
    assert rules["allowed_fk_suffixes"] == ["_fkey"]
    assert rules["allowed_pk_prefixes"] == []
    assert rules["allowed_pk_suffixes"] == ["_pkey"]


@pytest.mark.unit
def test__resolve_naming_rules__category_not_in_convention__keeps_defaults() -> None:
    metadata = MetaData(naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"})

    rules = MigrationNamingMixin()._resolve_naming_rules(metadata)

    for category in ("index", "check", "uq", "pk"):
        for side in ("prefixes", "suffixes"):
            attr = f"allowed_{category}_{side}"
            assert rules[attr] == MigrationNamingMixin._DEFAULTS[attr]


@pytest.mark.unit
def test__resolve_naming_rules__fully_dynamic_template__keeps_defaults() -> None:
    metadata = MetaData(naming_convention={"fk": "%(table_name)s_%(column_0_name)s", "pk": "pk_%(table_name)s"})

    rules = MigrationNamingMixin()._resolve_naming_rules(metadata)

    assert rules["allowed_fk_prefixes"] == ["fk_"]
    assert rules["allowed_fk_suffixes"] == ["_fkey"]


@pytest.mark.unit
def test__resolve_naming_rules__ix_and_uq__uq_rules_join_the_index_rules() -> None:
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
        }
    )

    rules = MigrationNamingMixin()._resolve_naming_rules(metadata)

    assert sorted(rules["allowed_index_prefixes"]) == ["ix_", "uq_"]
    assert rules["allowed_index_suffixes"] == []


@pytest.mark.unit
def test__resolve_naming_rules__explicit_attribute__overrides_convention() -> None:
    class _Explicit(MigrationNamingMixin):
        allowed_fk_suffixes: ClassVar[object] = ["_fkey"]

    metadata = MetaData(naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"})

    rules = _Explicit()._resolve_naming_rules(metadata)

    assert rules["allowed_fk_prefixes"] == ["fk_"]
    assert rules["allowed_fk_suffixes"] == ["_fkey"]
