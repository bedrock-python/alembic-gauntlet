"""Unit tests for pytest fixtures."""

from pathlib import Path

import pytest
from alembic.config import Config

from alembic_gauntlet.fixtures import _create_alembic_config


@pytest.mark.unit
def test__create_alembic_config__file_not_found__raises_error(tmp_path: Path) -> None:
    # Arrange
    non_existent_path = tmp_path / "does_not_exist.ini"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match=r"alembic\.ini not found"):
        _create_alembic_config(non_existent_path)


@pytest.mark.unit
def test__create_alembic_config__valid_file__returns_config(tmp_path: Path) -> None:
    # Arrange
    ini_path = tmp_path / "alembic.ini"
    ini_path.write_text(
        """[alembic]
script_location = my_migrations
""",
        encoding="utf-8",
    )

    # Act
    config = _create_alembic_config(ini_path)

    # Assert
    assert isinstance(config, Config)
    assert config.get_main_option("script_location") == "my_migrations"


@pytest.mark.unit
def test__create_alembic_config__no_script_location__sets_default(tmp_path: Path) -> None:
    # Arrange
    ini_path = tmp_path / "alembic.ini"
    ini_path.write_text(
        """[alembic]
""",
        encoding="utf-8",
    )

    # Act
    config = _create_alembic_config(ini_path)

    # Assert
    assert config.get_main_option("script_location") == "migrations"
