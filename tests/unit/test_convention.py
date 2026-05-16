"""Unit tests for naming convention derivation from SQLAlchemy MetaData."""

import pytest
from sqlalchemy import MetaData

from alembic_gauntlet.utils.convention import (
    _extract_prefix,
    _extract_suffix,
    rules_from_metadata,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("fk_%(table_name)s_%(column_0_name)s", "fk_"),
        ("%(table_name)s_%(column_0_name)s_fkey", None),
        ("no_placeholders", None),
    ],
    ids=["has_prefix", "no_prefix", "no_placeholders"],
)
def test__extract_prefix(template: str, expected: str | None) -> None:
    assert _extract_prefix(template) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("%(table_name)s_%(column_0_name)s_fkey", "_fkey"),
        ("fk_%(table_name)s_%(column_0_name)s", None),
        ("no_placeholders", None),
    ],
    ids=["has_suffix", "no_suffix", "no_placeholders"],
)
def test__extract_suffix(template: str, expected: str | None) -> None:
    assert _extract_suffix(template) == expected


@pytest.mark.unit
def test__rules_from_metadata__no_convention__returns_empty_rules() -> None:
    metadata = MetaData()
    rules = rules_from_metadata(metadata)

    assert rules.index_prefixes == []
    assert rules.index_suffixes == []
    assert rules.fk_prefixes == []
    assert rules.fk_suffixes == []
    assert rules.check_prefixes == []
    assert rules.check_suffixes == []
    assert rules.uq_prefixes == []
    assert rules.uq_suffixes == []
    assert rules.pk_prefixes == []
    assert rules.pk_suffixes == []


@pytest.mark.unit
def test__rules_from_metadata__sqlalchemy_default_convention__returns_empty_rules() -> None:
    # SQLAlchemy default: {"ix": "ix_%(column_0_label)s"} — should be ignored
    metadata = MetaData()
    assert set(metadata.naming_convention.keys()) == {"ix"}

    rules = rules_from_metadata(metadata)

    assert rules.index_prefixes == []
    assert rules.fk_prefixes == []


@pytest.mark.unit
def test__rules_from_metadata__full_convention__extracts_all_rules() -> None:
    convention = {
        "ix": "%(column_0_label)s_idx",
        "uq": "%(table_name)s_%(column_0_name)s_key",
        "ck": "%(table_name)s_%(constraint_name)s_check",
        "fk": "%(table_name)s_%(column_0_name)s_fkey",
        "pk": "%(table_name)s_pkey",
    }
    metadata = MetaData(naming_convention=convention)
    rules = rules_from_metadata(metadata)

    assert rules.index_prefixes == []
    assert rules.index_suffixes == ["_idx"]
    assert rules.uq_prefixes == []
    assert rules.uq_suffixes == ["_key"]
    assert rules.check_prefixes == []
    assert rules.check_suffixes == ["_check"]
    assert rules.fk_prefixes == []
    assert rules.fk_suffixes == ["_fkey"]
    assert rules.pk_prefixes == []
    assert rules.pk_suffixes == ["_pkey"]


@pytest.mark.unit
def test__rules_from_metadata__prefix_based_convention__extracts_prefixes() -> None:
    convention = {
        "ix": "idx_%(column_0_label)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "ck": "chk_%(table_name)s_%(constraint_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "pk": "pk_%(table_name)s",
    }
    metadata = MetaData(naming_convention=convention)
    rules = rules_from_metadata(metadata)

    assert rules.index_prefixes == ["idx_"]
    assert rules.index_suffixes == []
    assert rules.fk_prefixes == ["fk_"]
    assert rules.fk_suffixes == []
    assert rules.check_prefixes == ["chk_"]
    assert rules.check_suffixes == []
    assert rules.uq_prefixes == ["uq_"]
    assert rules.uq_suffixes == []
    assert rules.pk_prefixes == ["pk_"]
    assert rules.pk_suffixes == []


@pytest.mark.unit
def test__rules_from_metadata__fully_dynamic_template__extracts_nothing() -> None:
    # No literal prefix or suffix — should be ignored gracefully
    convention = {
        "fk": "%(table_name)s_%(column_0_name)s",
        "pk": "%(table_name)s",
    }
    metadata = MetaData(naming_convention=convention)
    rules = rules_from_metadata(metadata)

    assert rules.fk_prefixes == []
    assert rules.fk_suffixes == []
    assert rules.pk_prefixes == []
    assert rules.pk_suffixes == []


@pytest.mark.unit
def test__rules_from_metadata__both_prefix_and_suffix__extracts_both() -> None:
    convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_fkey",
    }
    metadata = MetaData(naming_convention=convention)
    rules = rules_from_metadata(metadata)

    assert rules.fk_prefixes == ["fk_"]
    assert rules.fk_suffixes == ["_fkey"]


@pytest.mark.unit
def test__rules_from_metadata__partial_convention__only_extracts_present_keys() -> None:
    convention = {
        "fk": "%(table_name)s_%(column_0_name)s_fkey",
        "pk": "%(table_name)s_pkey",
    }
    metadata = MetaData(naming_convention=convention)
    rules = rules_from_metadata(metadata)

    assert rules.fk_suffixes == ["_fkey"]
    assert rules.pk_suffixes == ["_pkey"]
    assert rules.index_prefixes == []
    assert rules.uq_prefixes == []
    assert rules.check_prefixes == []
