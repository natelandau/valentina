"""Main file which instantiates the bot and runs it."""

import logging
import sys
from pathlib import Path
from typing import Optional

import discord
import typer
from loguru import logger

from valentina.models.bot import Valentina
from valentina.utils import InterceptHandler
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


http_log_level = get_config_value("VALENTINA_LOG_LEVEL_HTTP", "INFO")
aws_log_level = get_config_value("VALENTINA_LOG_LEVEL_AWS", "INFO")

# Instantiate Logging
logging.getLogger("discord.http").setLevel(level=http_log_level.upper())
logging.getLogger("discord.gateway").setLevel(level=http_log_level.upper())
logging.getLogger("discord.webhook").setLevel(level=http_log_level.upper())
logging.getLogger("discord.client").setLevel(level=http_log_level.upper())
logging.getLogger("faker").setLevel(level="INFO")
for service in ["urllib3", "boto3", "botocore", "s3transfer"]:
    logging.getLogger(service).setLevel(level=aws_log_level.upper())

logger.remove()
logger.add(
    sys.stderr,
    level=get_config_value("VALENTINA_LOG_LEVEL", "INFO").upper(),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>",
    enqueue=True,
)
logger.add(
    get_config_value("VALENTINA_LOG_FILE", "valentina.log"),
    level=get_config_value("VALENTINA_LOG_LEVEL", "INFO").upper(),
    rotation="1 week",
    retention="2 weeks",
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
