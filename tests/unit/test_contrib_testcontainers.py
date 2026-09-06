"""Unit tests for the testcontainers contrib fixture."""

import sys
import types
import warnings

import pytest

from alembic_gauntlet.contrib.testcontainers import _import_postgres_container


@pytest.mark.unit
def test__import_postgres_container__current_testcontainers__no_deprecation_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange - a fresh import, as at the start of a test session
    monkeypatch.delitem(sys.modules, "testcontainers.postgres", raising=False)

    # Act
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        container_class = _import_postgres_container()

    # Assert
    assert container_class.__name__ == "PostgresContainer"


@pytest.mark.unit
def test__import_postgres_container__no_community_package__falls_back_to_legacy_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange - testcontainers < 4.15.0 ships PostgresContainer only under testcontainers.postgres
    legacy = types.ModuleType("testcontainers.postgres")
    legacy.PostgresContainer = object()
    monkeypatch.setitem(sys.modules, "testcontainers.community.postgres", None)
    monkeypatch.setitem(sys.modules, "testcontainers.postgres", legacy)

    # Act
    container_class = _import_postgres_container()

    # Assert
    assert container_class is legacy.PostgresContainer


@pytest.mark.unit
def test__import_postgres_container__not_installed__raises_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setitem(sys.modules, "testcontainers.community.postgres", None)
    monkeypatch.setitem(sys.modules, "testcontainers.postgres", None)

    # Act & Assert
    with pytest.raises(ImportError, match=r"alembic-gauntlet\[testcontainers\]"):
        _import_postgres_container()
