# type: ignore
"""Shared fixtures for tests."""

import logging
from unittest.mock import MagicMock

import discord
import pytest
import pytest_asyncio
from discord.ext import commands
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from rich import print

from valentina.constants import CONFIG
from valentina.utils.database import init_database


@pytest_asyncio.fixture(autouse=True)
async def _init_database(request):
    """Initialize the database."""
    if "no_db" in request.keywords:
        # when '@pytest.mark.no_db()' is called, this fixture will not run
        yield
    else:  # Create Motor client
        client = AsyncIOMotorClient(
            f"{CONFIG['VALENTINA_TEST_MONGO_URI']}/{CONFIG['VALENTINA_TEST_MONGO_DATABASE_NAME']}",
            tz_aware=True,
        )

        if "drop_db" in request.keywords:
            # Drop the database after the test
            await client.drop_database(CONFIG["VALENTINA_TEST_MONGO_DATABASE_NAME"])

        # Initialize beanie with the Sample document class and a database
        await init_database(
            client=client, database=client[CONFIG["VALENTINA_TEST_MONGO_DATABASE_NAME"]]
        )

        yield


### Mock discord.py objects ###
@pytest.fixture()
def mock_interaction1(mocker, mock_guild1, mock_member):
    """A mock of a discord.Interaction object."""
    mock_interaction = mocker.MagicMock()
    mock_interaction.id = 1
    mock_interaction.guild = mock_guild1
    mock_interaction.author = mock_member

    mock_interaction.__class__ = discord.Interaction

    return mock_interaction


@pytest.fixture()
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


@pytest.fixture()
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


@pytest.fixture()
def mock_guild1(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 1
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest.fixture()
def mock_guild2(mocker):
    """A mock of a discord.Guild object."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 2
    mock_guild.name = "Test Guild2"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    return mock_guild


@pytest.fixture()
def mock_ctx1(mocker, mock_member, mock_guild1, mock_interaction1):
    """Create a mock context object with user 1."""
    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.user_svc.update_or_add = MagicMock(return_value=mock_member)
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
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture()
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


### Factories for Database Classes ###
