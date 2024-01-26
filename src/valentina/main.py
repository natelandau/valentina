"""Main file which instantiates the bot and runs it."""

from pathlib import Path
from time import sleep
from typing import Optional

import discord
import typer
from loguru import logger

from valentina.models.bot import Valentina
from valentina.utils import instantiate_logger
from valentina.utils.database import test_db_connection
from valentina.utils.helpers import get_config_value

from .__version__ import __version__

# Instantiate Typer
app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
typer.rich_utils.STYLE_HELPTEXT = ""


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__package__} version: {__version__}")  # noqa: T201
        raise typer.Exit()


@app.command()
def main(
    version: Optional[bool] = typer.Option(  # noqa: ARG001
        None, "--version", help="Print version and exit", callback=version_callback, is_eager=True
    ),
) -> None:
    """Run Valentina."""
    # Instantiate the logger
    instantiate_logger()

    # Ensure the database is available before starting the bot
    while not test_db_connection():
        logger.error("DB: Connection failed. Retrying in 30 seconds...")
        sleep(30)

    # Instantiate the bot
    intents = discord.Intents.all()
    bot = Valentina(
        debug_guilds=[int(g) for g in get_config_value("VALENTINA_GUILDS", "").split(",")],
        intents=intents,
        owner_ids=[int(o) for o in get_config_value("VALENTINA_OWNER_IDS", "").split(",")],
        parent_dir=Path(__file__).parents[2].absolute(),
        command_prefix="∑",  # Effectively remove the command prefix by setting it to 'sigma'
        version=__version__,
    )

    bot.run(get_config_value("VALENTINA_DISCORD_TOKEN"))  # run the bot
