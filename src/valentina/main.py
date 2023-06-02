"""Main file which instantiates the bot and runs it."""
import logging
import sys
from pathlib import Path
from typing import Optional

import discord
import typer
from dotenv import dotenv_values
from loguru import logger

from valentina import __version__
from valentina.models import Valentina
from valentina.utils import InterceptHandler

# Import configuration from environment variables
DIR = Path(__file__).parents[2].absolute()
config = {
    **dotenv_values(DIR / ".env.shared"),  # load shared variables
    **dotenv_values(DIR / ".env.secret"),  # load sensitive variables
    # **os.environ,  # override loaded values with environment variables
}
DIR = Path(__file__).parents[2].absolute()

# Instantiate Logging
logger.remove()
logger.add(sys.stderr, level=config["LOG_LEVEL"])
logger.add(
    config["LOG_FILE"],
    level=config["LOG_LEVEL"],
    rotation="10 MB",
    compression="zip",
    enqueue=True,
)

# Intercept standard discord.py logs and redirect to Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Instantiate Typer
app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
typer.rich_utils.STYLE_HELPTEXT = ""


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__package__} version: {__version__}")
        raise typer.Exit()


@app.command()
def main(
    version: Optional[bool] = typer.Option(  # noqa: ARG001
        None, "--version", help="Print version and exit", callback=version_callback, is_eager=True
    ),
) -> None:
    """Run Valentina."""
    intents = discord.Intents.all()
    bot = Valentina(
        intents=intents,
        debug_guilds=[int(g) for g in config["GUILDS"].split(",")],
        parent_dir=DIR,
    )

    bot.run(config["DISCORD_TOKEN"])  # run the bot
