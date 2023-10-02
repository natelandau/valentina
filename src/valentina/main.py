"""Main file which instantiates the bot and runs it."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import discord
import typer
from dotenv import dotenv_values
from loguru import logger

from valentina.models import DatabaseService
from valentina.models.bot import Valentina
from valentina.models.db_tables import DATABASE
from valentina.utils import InterceptHandler

from .__version__ import __version__

# Instantiate Typer
app = typer.Typer(add_completion=False, no_args_is_help=True, rich_markup_mode="rich")
typer.rich_utils.STYLE_HELPTEXT = ""


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"{__package__} version: {__version__}")  # noqa: T201
        raise typer.Exit()


# Import configuration from environment variables
DIR = Path(__file__).parents[2].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}
for k, v in CONFIG.items():
    CONFIG[k] = v.replace('"', "").replace("'", "").replace(" ", "")


# Instantiate Logging
logging.getLogger("discord.http").setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_HTTP"].upper())
logging.getLogger("discord.gateway").setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_HTTP"].upper())
logging.getLogger("discord.webhook").setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_HTTP"].upper())
logging.getLogger("discord.client").setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_HTTP"].upper())
logging.getLogger("peewee").setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_DB"].upper())
for service in ["urllib3", "boto3", "botocore", "s3transfer"]:
    logging.getLogger(service).setLevel(level=CONFIG["VALENTINA_LOG_LEVEL_AWS"].upper())

logger.remove()
logger.add(
    sys.stderr,
    level=CONFIG["VALENTINA_LOG_LEVEL"].upper(),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>",
    enqueue=True,
)
logger.add(
    CONFIG["VALENTINA_LOG_FILE"],
    level=CONFIG["VALENTINA_LOG_LEVEL"].upper(),
    rotation="5 MB",
    compression="zip",
    enqueue=True,
)

# Intercept standard discord.py logs and redirect to Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


@app.command()
def main(
    version: Optional[bool] = typer.Option(  # noqa: ARG001
        None, "--version", help="Print version and exit", callback=version_callback, is_eager=True
    ),
) -> None:
    """Run Valentina."""
    # Setup database
    db = DatabaseService(DATABASE)
    db.create_tables()
    db.initialize_database(__version__)

    # Instantiate the bot
    intents = discord.Intents.all()
    bot = Valentina(
        debug_guilds=[int(g) for g in CONFIG["VALENTINA_GUILDS"].split(",")],
        intents=intents,
        owner_ids=[int(o) for o in CONFIG["VALENTINA_OWNER_IDS"].split(",")],
        parent_dir=DIR,
        config=CONFIG,
        command_prefix="∑",  # Effectively remove the command prefix by setting it to 'sigma'
        version=__version__,
    )

    bot.run(CONFIG["VALENTINA_DISCORD_TOKEN"])  # run the bot
