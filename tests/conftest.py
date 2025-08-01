# type: ignore
"""Shared fixtures for tests."""

import logging
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import discord
import docker
import pytest
import pytest_asyncio
from discord.ext import commands
from loguru import logger
from pymongo import AsyncMongoClient
from rich import print as rprint

from valentina.utils import ValentinaConfig, console
from valentina.utils.database import init_database, test_db_connection

### Constants for Testing ###
CHANNEL_CHARACTER_ID = 1234567890
CHANNEL_BOOK_ID = 1234567891
CHANNEL_CATEGORY_CAMPAIGN_ID = 1234567892
GUILD_ID = 1


@pytest.fixture(scope="session", autouse=True)
def start_mongo_container():
    """Create a Docker client and start a MongoDB container if mongodb is not running.

    This fixture is automatically run before all tests.
    """
    container = None
    if not test_db_connection():
        rprint("Creating Docker client")
        client = docker.from_env()
        rprint("Creating MongoDB container")
        container = client.containers.run(
            image="mongo:latest",
            ports={"27017/tcp": 27017},
            name="valentina-pytest-mongo",
            detach=True,
            auto_remove=True,
        )
        rprint(f"MongoDB container created: {container.id}")

        if not test_db_connection():
            pytest.exit(
                "\n\n-----\nMongoDB is not running\nrun `docker compose up` in the tests directory to start it\n-----\n"
            )

    yield
    if container:
        rprint("Stopping MongoDB container")
        container.stop()


## Database initialization ##
@pytest_asyncio.fixture(autouse=True)
async def _init_database(request) -> None:
    """Initialize the database."""
    if "no_db" in request.keywords:
        # when '@pytest.mark.no_db()' is called, this fixture will not run
        yield
    else:  # Create Motor client
        client = AsyncMongoClient(
            f"{ValentinaConfig().test_mongo_uri}/{ValentinaConfig().test_mongo_database_name}",
            tz_aware=True,
        )

        # when '@pytest.mark.drop_db()' is called, the database will be dropped before the test
        if "drop_db" in request.keywords:
            # Drop the database after the test
            await client.drop_database(ValentinaConfig().test_mongo_database_name)

        # Initialize beanie with the Sample document class and a database
        await init_database(
            client=client,
            database=client[ValentinaConfig().test_mongo_database_name],
        )

        yield
        await client.close()


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
    mocker,
    mock_member,
    mock_guild1,
    mock_interaction1,
    mock_discord_character_channel,
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
        def emit(self, record):  # noqa: ANN202
            logging.getLogger(record.name).handle(record)

    logger.add(
        PropagateHandler(),
        format="{message}",
    )  # shunt logs into the standard python logging machinery
    # caplog.set_level(0)  # Tell logging to handle all log levels
    return caplog


@pytest.fixture
def debug(tmp_path: Path) -> Callable[[str | Path, str, int, bool], bool]:
    """Return a debug printing function for test development and troubleshooting.

    Create and return a function that prints formatted debug output to the console during test development and debugging. The returned function allows printing variables, file contents, or directory structures with clear visual separation and optional breakpoints.

    Returns:
        Callable[[str | Path, str, bool, int], bool]: A function that prints debug info with
            the following parameters:
            - value: The data to debug print (string or Path)
            - label: Optional header text for the output
            - breakpoint: Whether to pause execution after printing
            - width: Maximum output width in characters

    Example:
        def test_complex_data(debug):
            result = process_data()
            debug(result, "Processed Data", breakpoint=True)
    """

    def _debug_inner(
        value: str | Path,
        label: str = "",
        width: int = 80,
        *,
        pause: bool = False,
        strip_tmp_path: bool = True,
    ) -> bool:
        """Print debug information during test development and debugging sessions.

        Print formatted debug output to the console with an optional breakpoint. This is particularly useful when developing or debugging tests to inspect variables, file contents, or directory structures. The output is formatted with a labeled header and footer rule for clear visual separation.

        Args:
            value (Union[str, Path]): The value to debug print. If a Path to a directory is provided, recursively prints all files in that directory tree.
            label (str): Optional header text to display above the debug output for context.
            pause (bool, optional): If True, raises a pytest.fail() after printing to pause execution. Defaults to False.
            width (int, optional): Maximum width in characters for the console output. Matches pytest's default width of 80 when running without the -s flag. Defaults to 80.
            strip_tmp_path (bool, optional): If True, strip the tmp_path from the output. Defaults to True.

        Returns:
            bool: Always returns True unless pause=True, in which case raises pytest.fail()

        Example:
            def test_something(debug):
                # Print contents of a directory
                debug(Path("./test_data"), "Test Data Files")

                # Print a variable with a breakpoint
                debug(my_var, "Debug my_var", pause=True)
        """
        console.rule(label or "")

        # If a directory is passed, print the contents
        if isinstance(value, Path) and value.is_dir():
            for p in value.rglob("*"):
                if strip_tmp_path and p.relative_to(tmp_path):
                    console.print(f"…/{p.relative_to(tmp_path)!s}", width=width)
                    continue

                console.print(p, width=width)
        else:
            if strip_tmp_path:
                value = str(value).replace(str(tmp_path), "…")
            console.print(value, width=width)

        console.rule()

        if pause:  # pragma: no cover
            return pytest.fail("Breakpoint")

        return True

    return _debug_inner  # type: ignore [return-value]
