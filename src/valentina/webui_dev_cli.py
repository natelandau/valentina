"""Start webui without Discord bot for debugging and development."""

from typing import Annotated

import typer

from valentina.constants import LogLevel
from valentina.utils import ValentinaConfig, instantiate_logger
from valentina.webui import create_app

# Instantiate Typer
cli = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
typer.rich_utils.STYLE_HELPTEXT = ""


@cli.command()
def main(
    verbosity: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            show_default=True,
            help="""Set verbosity level(0=INFO, 1=DEBUG, 2=TRACE)""",
            count=True,
        ),
    ] = 0,
) -> None:
    """Run the web server for development."""
    if verbosity == 0:
        log_level = LogLevel.INFO
    elif verbosity == 1:
        log_level = LogLevel.DEBUG
    elif verbosity >= 2:  # noqa: PLR2004
        log_level = LogLevel.TRACE

    instantiate_logger(log_level=log_level)

    app = create_app(environment="Development")
    app.run(
        host=ValentinaConfig().webui_host,
        port=int(ValentinaConfig().webui_port),
        debug=True,
        use_reloader=True,
    )
