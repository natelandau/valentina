"""The Group CLI."""

from pathlib import Path
from typing import Any, Optional

import typer

from the_group.__version__ import __version__
from the_group.config import Config
from the_group.utils import alerts
from the_group.utils.alerts import logger as log
from the_group.utils.console import console

app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")

typer.rich_utils.STYLE_HELPTEXT = ""


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"{__package__} version: {__version__}")
        raise typer.Exit()


@app.command()
def main(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Dry run - don't actually change anything",
    ),
    config_file: Path = typer.Option(
        Path(Path.home() / f".{__package__}/{__package__}.toml"),
        help="Specify a custom path to configuration file.",
        show_default=False,
        dir_okay=False,
        file_okay=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force changes without prompting for confirmation. Use with caution!",
        show_default=True,
    ),
    log_file: Path = typer.Option(
        Path(Path.home() / "logs" / f"{__package__}.log"),
        help="Path to log file",
        show_default=True,
        dir_okay=False,
        file_okay=True,
        exists=False,
    ),
    log_to_file: bool = typer.Option(
        False,
        "--log-to-file",
        help="Log to file",
        show_default=True,
    ),
    verbosity: int = typer.Option(
        0,
        "-v",
        "--verbose",
        show_default=False,
        help="""Set verbosity level (0=WARN, 1=INFO, 2=DEBUG, 3=TRACE)""",
        count=True,
    ),
    message: str = "",
    version: Optional[bool] = typer.Option( # noqa: ARG001
        None, "--version", help="Print version and exit", callback=version_callback, is_eager=True
    ),
) -> None:
    """Say a message."""
    alerts.LoggerManager(  # pragma: no cover
        log_file,
        verbosity,
        log_to_file,
    )
    context: dict[str, Any] = {
        "dry_run": dry_run,
        "force": force,
    }
    log.trace(f"Context: {context}")
    config: Config = Config(
        config_path=config_file,
        context=context,
    )
    log.debug(f"Loaded config: {config_file}")
    log.trace(f"Config: {config}")

    if message:
        typer.echo(message)
        log.info(message)
