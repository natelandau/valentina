# type: ignore
"""Test configuration model."""
import filecmp
import shutil
from pathlib import Path

import pytest
import typer

from the_group.config.config import PATH_CONFIG_DEFAULT, Config


def test_init_config_1():
    """Test initializing a configuration file.

    GIVEN a request to initialize a configuration file
    WHEN no path is provided
    THEN raise an exception
    """
    with pytest.raises(typer.Exit):
        Config()


def test_init_config_2(tmp_path):
    """Test initializing a configuration file.

    GIVEN a request to initialize a configuration file
    WHEN a path to a non-existent file is provided
    THEN create the default configuration file and exit
    """
    config_path = Path(tmp_path / "config.toml")
    with pytest.raises(typer.Exit):
        Config(config_path=config_path)
    assert config_path.exists()
    assert filecmp.cmp(config_path, PATH_CONFIG_DEFAULT) is True


def test_init_config_3(tmp_path):
    """Test initializing a configuration file.

    GIVEN a request to initialize a configuration file
    WHEN a path to the default configuration file is provided
    THEN load the configuration file
    """
    path_to_config = Path(tmp_path / "config.toml")
    shutil.copy(PATH_CONFIG_DEFAULT, path_to_config)
    config = Config(config_path=path_to_config)
    assert config.config_path == path_to_config
    assert config.config == {"key": "value", "parent": {"key": "value"}}
    assert config.context == {}
    assert config.dry_run is False
    assert config.force is False


def test_init_config_4(tmp_path):
    """Test initializing a configuration file.

    GIVEN a request to initialize a configuration file
    WHEN values are provided in the context
    THEN load the configuration file
    """
    path_to_config = Path(tmp_path / "config.toml")
    shutil.copy(PATH_CONFIG_DEFAULT, path_to_config)
    config = Config(config_path=path_to_config, context={"dry_run": True, "force": True})
    assert config.config_path == path_to_config
    assert config.config == {"key": "value", "parent": {"key": "value"}}
    assert config.context == {"dry_run": True, "force": True}
    assert config.dry_run is True
    assert config.force is True
