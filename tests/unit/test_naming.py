"""Unit tests for naming convention validation."""

import pytest

from alembic_gauntlet.utils.naming import validate_naming_results

_PREFIXES = ["idx_", "uq_"]
_SUFFIXES = ["_idx", "_pkey", "_key"]
_FK_SUFFIXES = ["_fkey"]
_FK_PREFIXES = ["fk_"]
_CHK_PREFIXES = ["chk_"]
_CHK_SUFFIXES: list[str] = []
_UQ_PREFIXES = ["uq_"]
_UQ_SUFFIXES: list[str] = []
_PK_PREFIXES = ["pk_"]
_PK_SUFFIXES = ["_pkey"]


def _empty_table(
    indexes: set[str] | None = None,
    fks: list[dict] | None = None,  # type: ignore[type-arg]
    check_constraints: set[str] | None = None,
    unique_constraints: set[str] | None = None,
    pk_constraint: str | None = None,
) -> dict:  # type: ignore[type-arg]
    return {
        "indexes": indexes or set(),
        "fks": fks or [],
        "check_constraints": check_constraints or set(),
        "unique_constraints": unique_constraints or set(),
        "pk_constraint": pk_constraint,
    }


def _call(results: dict, **kwargs) -> None:  # type: ignore[type-arg]
    defaults = {
        "allowed_index_prefixes": _PREFIXES,
        "allowed_index_suffixes": _SUFFIXES,
        "allowed_fk_suffixes": _FK_SUFFIXES,
        "allowed_fk_prefixes": _FK_PREFIXES,
        "allowed_check_prefixes": _CHK_PREFIXES,
        "allowed_check_suffixes": _CHK_SUFFIXES,
        "allowed_uq_prefixes": _UQ_PREFIXES,
        "allowed_uq_suffixes": _UQ_SUFFIXES,
        "allowed_pk_prefixes": _PK_PREFIXES,
        "allowed_pk_suffixes": _PK_SUFFIXES,
    }
    defaults.update(kwargs)
    validate_naming_results(results, **defaults)


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
    results = {"users": _empty_table(indexes={index_name})}

    # Act & Assert
    _call(results)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fk_dict", "test_id"),
    [
        ({"name": "profiles_user_id_fkey"}, "with_suffix"),
        ({"name": "fk_profiles_user_id_users"}, "with_prefix"),
        ({"constrained_columns": ["user_id"]}, "without_name"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test__validate_naming_results__valid_fk__passes(fk_dict: dict, test_id: str) -> None:  # type: ignore[type-arg]
    # Arrange
    results = {"profiles": _empty_table(fks=[fk_dict])}

    # Act & Assert
    _call(results)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("results", "error_match"),
    [
        ({"users": _empty_table(indexes={"bad_index_name"})}, "bad_index_name"),
        ({"profiles": _empty_table(fks=[{"name": "profiles_user_id_foreign"}])}, "profiles_user_id_foreign"),
    ],
    ids=["invalid_index", "invalid_fk"],
)
def test__validate_naming_results__invalid_name__raises_assertion_error(results: dict, error_match: str) -> None:  # type: ignore[type-arg]
    # Arrange & Act & Assert
    with pytest.raises(AssertionError, match=error_match):
        _call(results)


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
    results = {"orders": _empty_table(fks=[{"name": fk_name}])}

    # Act & Assert
    _call(results)


@pytest.mark.unit
def test__validate_naming_results__fk_prefix_overrides_suffix_requirement__passes() -> None:
    results = {"orders": _empty_table(fks=[{"name": "fk_orders_user_id_users"}])}

    _call(results)


@pytest.mark.unit
def test__validate_naming_results__fk_invalid_with_prefixes_configured__raises() -> None:
    results = {"orders": _empty_table(fks=[{"name": "orders_user_id_foreign"}])}

    with pytest.raises(AssertionError, match="orders_user_id_foreign"):
        _call(results)


@pytest.mark.unit
@pytest.mark.parametrize(
    "chk_name",
    ["chk_orders_amount_positive", "chk_users_age"],
    ids=["chk_orders", "chk_users"],
)
def test__validate_naming_results__valid_check_constraint__passes(chk_name: str) -> None:
    results = {"orders": _empty_table(check_constraints={chk_name})}

    _call(results)


@pytest.mark.unit
def test__validate_naming_results__invalid_check_constraint__raises() -> None:
    results = {"orders": _empty_table(check_constraints={"orders_amount_check"})}

    with pytest.raises(AssertionError, match="orders_amount_check"):
        _call(results)


@pytest.mark.unit
@pytest.mark.parametrize(
    "uq_name",
    ["uq_users_email", "uq_profiles_slug"],
    ids=["uq_users", "uq_profiles"],
)
def test__validate_naming_results__valid_unique_constraint__passes(uq_name: str) -> None:
    results = {"users": _empty_table(unique_constraints={uq_name})}

    _call(results)


@pytest.mark.unit
def test__validate_naming_results__invalid_unique_constraint__raises() -> None:
    results = {"users": _empty_table(unique_constraints={"users_email_unique"})}

    with pytest.raises(AssertionError, match="users_email_unique"):
        _call(results)


@pytest.mark.unit
@pytest.mark.parametrize(
    "pk_name",
    ["pk_users", "users_pkey"],
    ids=["pk_prefix", "pkey_suffix"],
)
def test__validate_naming_results__valid_pk_constraint__passes(pk_name: str) -> None:
    results = {"users": _empty_table(pk_constraint=pk_name)}

    _call(results)


@pytest.mark.unit
def test__validate_naming_results__invalid_pk_constraint__raises() -> None:
    results = {"users": _empty_table(pk_constraint="primary_users")}

    with pytest.raises(AssertionError, match="primary_users"):
        _call(results)


@pytest.mark.unit
def test__validate_naming_results__unnamed_pk_constraint__passes() -> None:
    results = {"users": _empty_table(pk_constraint=None)}

    _call(results)


@pytest.mark.unit
def test__validate_naming_results__empty_results__passes() -> None:
    # Arrange
    results = {}

    # Act & Assert
    _call(results)


@pytest.mark.unit
def test__validate_naming_results__multiple_valid_tables__passes() -> None:
    # Arrange
    results = {
        "users": _empty_table(
            indexes={"users_pkey", "uq_users_email"},
            check_constraints={"chk_users_age"},
            unique_constraints={"uq_users_email"},
            pk_constraint="pk_users",
        ),
        "profiles": _empty_table(
            indexes={"profiles_pkey", "idx_profiles_user_id"},
            fks=[{"name": "fk_profiles_user_id_users"}],
            pk_constraint="profiles_pkey",
        ),
    }

    # Act & Assert
    _call(results)
