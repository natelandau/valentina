# type: ignore
"""Test the-group CLI."""

from pathlib import Path

from typer.testing import CliRunner

from the_group.cli import app
from tests.helpers import Regex

runner = CliRunner()


def test_version():
    """Test printing version and then exiting."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output == Regex(r"the_group version: \d+\.\d+\.\d+$")


def test_specify_config_location(tmp_path):
    """Test specifying the location of the config file."""
    config_path = Path(tmp_path / "config.toml")
    assert config_path.exists() is False

    result = runner.invoke(app, ["--config-file", config_path])
    print(result.output)
    assert result.exit_code == 1
    assert "SUCCESS  | Created default configuration file" in result.output
    assert "NOTICE   | Please edit" in result.output

    result = runner.invoke(app, ["--config-file", config_path])
    print(result.output)
    assert result.exit_code == 0
