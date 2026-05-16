"""Unit tests for naming convention validation."""

import pytest

from alembic_gauntlet.utils.naming import validate_naming_results

_PREFIXES = ["idx_", "uq_"]
_SUFFIXES = ["_idx", "_pkey", "_key"]
_FK_SUFFIXES = ["_fkey"]
_FK_PREFIXES = ["fk_"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "index_name",
    [
        "idx_users_email",
        "uq_users_email",
        "users_pkey",
        "users_email_idx",
        "users_pkey1",  # partition with numeric suffix
        "users_email_idx2",  # partition with numeric suffix
    ],
    ids=["idx_prefix", "uq_prefix", "pkey_suffix", "idx_suffix", "partition_pkey", "partition_idx"],
)
def test__validate_naming_results__valid_index_name__passes(index_name: str) -> None:
    # Arrange
    results = {"users": {"indexes": {index_name}, "fks": []}}

    # Act & Assert
    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, _FK_PREFIXES)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fk_dict", "test_id"),
    [
        ({"name": "profiles_user_id_fkey"}, "with_name"),
        ({"constrained_columns": ["user_id"]}, "without_name"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test__validate_naming_results__valid_fk__passes(fk_dict: dict, test_id: str) -> None:
    # Arrange
    results = {"profiles": {"indexes": set(), "fks": [fk_dict]}}

    # Act & Assert
    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, _FK_PREFIXES)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("results", "error_match"),
    [
        ({"users": {"indexes": {"bad_index_name"}, "fks": []}}, "bad_index_name"),
        ({"profiles": {"indexes": set(), "fks": [{"name": "profiles_user_id_foreign"}]}}, "profiles_user_id_foreign"),
    ],
    ids=["invalid_index", "invalid_fk"],
)
def test__validate_naming_results__invalid_name__raises_assertion_error(results: dict, error_match: str) -> None:
    # Arrange & Act & Assert
    with pytest.raises(AssertionError, match=error_match):
        validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, _FK_PREFIXES)


@pytest.mark.unit
@pytest.mark.parametrize(
    "fk_name",
    [
        "fk_orders_user_id_users",
        "fk_profiles_account_id_accounts",
    ],
    ids=["fk_prefix_orders", "fk_prefix_profiles"],
)
def test__validate_naming_results__valid_fk_prefix__passes(fk_name: str) -> None:
    # Arrange
    results = {"orders": {"indexes": set(), "fks": [{"name": fk_name}]}}

    # Act & Assert
    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, allowed_fk_prefixes=_FK_PREFIXES)


@pytest.mark.unit
def test__validate_naming_results__fk_prefix_overrides_suffix_requirement__passes() -> None:
    # A name that matches the prefix but not any suffix should pass when prefixes are provided.
    results = {"orders": {"indexes": set(), "fks": [{"name": "fk_orders_user_id_users"}]}}

    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, allowed_fk_prefixes=_FK_PREFIXES)


@pytest.mark.unit
def test__validate_naming_results__fk_invalid_with_prefixes_configured__raises() -> None:
    # A name matching neither prefix nor suffix should still fail.
    results = {"orders": {"indexes": set(), "fks": [{"name": "orders_user_id_foreign"}]}}

    with pytest.raises(AssertionError, match="orders_user_id_foreign"):
        validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, allowed_fk_prefixes=_FK_PREFIXES)


@pytest.mark.unit
def test__validate_naming_results__empty_results__passes() -> None:
    # Arrange
    results = {}

    # Act & Assert
    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, _FK_PREFIXES)


@pytest.mark.unit
def test__validate_naming_results__multiple_valid_tables__passes() -> None:
    # Arrange
    results = {
        "users": {"indexes": {"users_pkey", "uq_users_email"}, "fks": []},
        "profiles": {
            "indexes": {"profiles_pkey", "idx_profiles_user_id"},
            "fks": [{"name": "profiles_user_id_fkey"}],
        },
    }

    # Act & Assert
    validate_naming_results(results, _PREFIXES, _SUFFIXES, _FK_SUFFIXES, _FK_PREFIXES)
