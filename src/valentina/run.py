"""Main file which instantiates the bot and runs it."""

import os
from time import sleep
from typing import Annotated

import typer
from loguru import logger

from valentina.constants import LogLevel, WebUIEnvironment
from valentina.utils import ValentinaConfig, debug_environment_variables, instantiate_logger
from valentina.utils.database import test_db_connection
from valentina.webui import configure_app

from .bot import bot

# Instantiate Typer
cli = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
typer.rich_utils.STYLE_HELPTEXT = ""


@cli.command()
def main(
    no_discord: Annotated[
        bool,
        typer.Option(
            "--no-discord",
            help="Only run the web server, not the discord bot. Good for quick development of web features that do not rely on Discord. Always runs in development mode.",
            is_flag=True,
        ),
    ] = False,
    dev_webui: Annotated[
        bool,
        typer.Option("--dev", help="Run WEBUI in development mode", is_flag=True),
    ] = False,
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
    """Run Valentina."""
    if verbosity == 0:
        log_level = LogLevel(ValentinaConfig().log_level)
    elif verbosity == 1:
        log_level = LogLevel.DEBUG
    elif verbosity >= 2:  # noqa: PLR2004
        log_level = LogLevel.TRACE

    instantiate_logger(log_level=log_level)

    # Print environment variables and ValentinaConfig settings if VALENTINA_TRACE is set
    if os.environ.get("VALENTINA_TRACE"):
        debug_environment_variables()

    # Ensure the database is available before starting the bot
    while not test_db_connection():
        logger.error("DB: Connection failed. Retrying in 30 seconds...")
        sleep(30)

    if no_discord:
        web_app = configure_app(WebUIEnvironment.DEVELOPMENT)
        web_app.run(
            host=ValentinaConfig().webui_host,
            port=int(ValentinaConfig().webui_port),
            debug=True,
            use_reloader=True,
        )
    else:
        bot.webui_mode = WebUIEnvironment.DEVELOPMENT if dev_webui else WebUIEnvironment.PRODUCTION
        bot.run(ValentinaConfig().discord_token)
