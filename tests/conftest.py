# type: ignore
"""Shared fixtures for tests."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock

import discord
import pytest
import pytest_asyncio
from discord.ext import commands
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from valentina.utils import ValentinaConfig, console
from valentina.utils.database import init_database

### Constants for Testing ###
CHANNEL_CHARACTER_ID = 1234567890
CHANNEL_BOOK_ID = 1234567891
CHANNEL_CATEGORY_CAMPAIGN_ID = 1234567892
GUILD_ID = 1


## Database initialization ##
@pytest_asyncio.fixture(autouse=True)
async def _init_database(request):
    """Initialize the database."""
    if "no_db" in request.keywords:
        # when '@pytest.mark.no_db()' is called, this fixture will not run
        yield
    else:  # Create Motor client
        client = AsyncIOMotorClient(
            f"{ValentinaConfig().test_mongo_uri}/{ValentinaConfig().test_mongo_database_name}",
            tz_aware=True,
        )

        # when '@pytest.mark.drop_db()' is called, the database will be dropped before the test
        if "drop_db" in request.keywords:
            # Drop the database after the test
            await client.drop_database(ValentinaConfig().test_mongo_database_name)

        # Initialize beanie with the Sample document class and a database
        await init_database(
            client=client, database=client[ValentinaConfig().test_mongo_database_name]
        )

        yield
        client.close()


### Mock discord.py objects ###
@pytest.fixture
def mock_bot(mocker):
    """A mock of a discord.Bot object."""
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot
    return mock_bot


@pytest.fixture
def mock_discord_campaign_category_channel(mocker):
    """A mock of a discord.CategoryChannel object associated with a campaign."""
    mock_channel_category = mocker.MagicMock()
    mock_channel_category.id = CHANNEL_CATEGORY_CAMPAIGN_ID
    mock_channel_category.name = "campaign-category"
    mock_channel_category.__class__ = discord.CategoryChannel

    return mock_channel_category


@pytest.fixture
def mock_discord_unassociated_category_channel(mocker):
    """A mock of a discord.CategoryChannel object associated with a campaign."""
    mock_channel = mocker.MagicMock()
    mock_channel.id = 2000001
    mock_channel.__class__ = discord.CategoryChannel
    return mock_channel


@pytest.fixture
def mock_discord_unassociated_channel(mocker, mock_discord_unassociated_category_channel):
    """A mock of a discord.Channel object associated with a book."""
    mock_channel = mocker.MagicMock()
    mock_channel.id = 1000002
    mock_channel.__class__ = discord.TextChannel
    mock_channel.category = mock_discord_unassociated_category_channel
    return mock_channel


@pytest.fixture
def mock_discord_character_channel(mocker, mock_discord_campaign_category_channel):
    """A mock of a discord.Channel object associated with a character."""
    mock_channel = mocker.MagicMock()
    mock_channel.id = CHANNEL_CHARACTER_ID
    mock_channel.__class__ = discord.TextChannel
    mock_channel.category = mock_discord_campaign_category_channel
    mock_channel.name = "character-channel"
    return mock_channel


@pytest.fixture
def mock_discord_book_channel(mocker, mock_discord_campaign_category_channel):
    """A mock of a discord.Channel object associated with a book."""
    mock_channel = mocker.MagicMock()
    mock_channel.id = CHANNEL_BOOK_ID
    mock_channel.__class__ = discord.TextChannel
    mock_channel.category = mock_discord_campaign_category_channel
    return mock_channel


@pytest.fixture
def mock_interaction1(mocker, mock_guild1, mock_member, mock_discord_character_channel):
    """A mock of a discord.Interaction object run in a character channel."""
    mock_interaction = mocker.MagicMock()
    mock_interaction.id = 1
    mock_interaction.guild = mock_guild1
    mock_interaction.author = mock_member
    mock_interaction.channel = mock_discord_character_channel

    mock_interaction.__class__ = discord.Interaction

    return mock_interaction


@pytest.fixture
def mock_member(mocker):
    """A mock of a discord.Member object."""
    mock_role_one = mocker.MagicMock()
    mock_role_one.id = 1
    mock_role_one.name = "@everyone"

    mock_role_two = mocker.MagicMock()
    mock_role_two.id = 2
    mock_role_two.name = "Player"

    mock_member = mocker.MagicMock()
    mock_member.id = 1
    mock_member.display_name = "Test User"
    mock_member.name = "testuser"
    mock_member.mention = "<@1>"
    mock_member.nick = "Testy"
    mock_member.__class__ = discord.Member
    mock_member.roles = [mock_role_one, mock_role_two]

    return mock_member


@pytest.fixture
def mock_member2(mocker):
    """A mock of a discord.Member object."""
    mock_role_one = mocker.MagicMock()
    mock_role_one.id = 1
    mock_role_one.name = "@everyone"

    mock_role_two = mocker.MagicMock()
    mock_role_two.id = 2
    mock_role_two.name = "Player"

    mock_guild = mocker.MagicMock()
    mock_guild.id = 200
    mock_guild.__class__ = discord.Guild

    mock_member = mocker.MagicMock()
    mock_member.id = 2
    mock_member.display_name = "Test User2"
    mock_member.name = "testuser2"
    mock_member.mention = "<@2>"
    mock_member.nick = "Testy2"
    mock_member.guild = mock_guild
    mock_member.__class__ = discord.Member
    mock_member.roles = [mock_role_one, mock_role_two]

    return mock_member


@pytest.fixture
def mock_guild1(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = GUILD_ID
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest.fixture
def mock_guild2(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 2
    mock_guild.name = "Test Guild2"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest_asyncio.fixture()
async def async_mock_ctx1(
    mocker, mock_member, mock_guild1, mock_interaction1, mock_discord_character_channel
):
    """Create an async mock context object with user 1 run in a character channel."""
    mock_bot = mocker.AsyncMock()
    mock_bot.__class__ = commands.Bot

    mock_options = mocker.AsyncMock()
    mock_options.__class__ = dict
    mock_options = {}

    # Mock the ctx object
    mock_ctx = mocker.AsyncMock()
    mock_ctx.interaction = mock_interaction1
    mock_ctx.author = mock_member
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild1
    mock_ctx.channel = mock_discord_character_channel
    mock_ctx.__class__ = discord.ApplicationContext

    # Mock the methods which post to audit and error logs
    mock_ctx.post_to_audit_log = AsyncMock()
    mock_ctx.post_to_error_log = AsyncMock()

    # Mock permissions as True
    mock_ctx.can_grant_xp = AsyncMock(return_value=True)
    mock_ctx.can_kill_character = AsyncMock(return_value=True)
    mock_ctx.can_manage_traits = AsyncMock(return_value=True)
    mock_ctx.can_manage_campaign = AsyncMock(return_value=True)

    return mock_ctx


@pytest.fixture
def mock_ctx1(mocker, mock_member, mock_guild1, mock_interaction1, mock_discord_character_channel):
    """Create a mock context object with user 1 run in a character channel."""
    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot

    mock_options = mocker.MagicMock()
    mock_options.__class__ = dict
    mock_options = {}

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.interaction = mock_interaction1
    mock_ctx.author = mock_member
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild1
    mock_ctx.channel = mock_discord_character_channel
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture
def caplog(caplog):
    """Override and wrap the caplog fixture with one of our own. This fixes a problem where loguru logs could not be captured by caplog."""
    logger.remove()  # remove default handler, if it exists
    # logger.enable("")  # enable all logs from all modules
    # logging.addLevelName(5, "TRACE")  # tell python logging how to interpret TRACE logs

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    logger.add(
        PropagateHandler(), format="{message}"
    )  # shunt logs into the standard python logging machinery
    # caplog.set_level(0)  # Tell logging to handle all log levels
    return caplog


@pytest.fixture
def debug():
    """Print debug information to the console. This is used to debug tests while writing them."""

    def _debug_inner(label: str, value: str | Path, breakpoint: bool = False):
        """Print debug information to the console. This is used to debug tests while writing them.

        Args:
            label (str): The label to print above the debug information.
            value (str | Path): The value to print. When this is a path, prints all files in the path.
            breakpoint (bool, optional): Whether to break after printing. Defaults to False.

        Returns:
            bool: Whether to break after printing.
        """
        console.rule(label)
        if not isinstance(value, Path) or not value.is_dir():
            console.print(value)
        else:
            for p in value.rglob("*"):
                console.print(p)

        console.rule()

        if breakpoint:
            return pytest.fail("Breakpoint")

        return True

    return _debug_inner


### Factories for Database Classes ###
