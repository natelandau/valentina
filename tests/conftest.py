# type: ignore
"""Shared fixtures for database tests.

This module contains shared fixtures that are used by multiple database tests.

Fixtures:
    mock_db: A mock database with test data for use in tests.
    empty_db: A database with no data for use in tests.
    mock_ctx: A context object with existing user(1)  and existing guild(1).
    mock_ctx2: A context object with existing user(1) and existing guild(2).
    mock_ctx3: A context object with a new user  and existing guild(1).
    mock_ctx4: A context object with a new user and a new guild.
    mock_member: A mock of a discord.Member object.
    caplog: Overwrite the built-in caplog fixture to capture loguru logs.
"""
import logging
from unittest.mock import MagicMock

import discord
import pytest
from discord.ext import commands
from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models.db_tables import (
    Campaign,
    CampaignChapter,
    CampaignNote,
    CampaignNPC,
    Character,
    CharacterClass,
    CustomSection,
    CustomTrait,
    DatabaseVersion,
    Guild,
    GuildUser,
    Macro,
    MacroTrait,
    RollProbability,
    RollStatistic,
    RollThumbnail,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    User,
    VampireClan,
)
from valentina.utils.db_initialize import PopulateDatabase

# IMPORTANT: This list must be kept in sync with all the models defined in src/valentina/models/database.py otherwise tests will write to the wrong database.
MODELS = [
    Character,
    CharacterClass,
    CustomSection,
    TraitCategory,
    CustomTrait,
    DatabaseVersion,
    Guild,
    Macro,
    RollThumbnail,
    User,
    VampireClan,
    Campaign,
    CampaignNote,
    CampaignChapter,
    CampaignNPC,
    Trait,
    TraitClass,
    TraitValue,
    GuildUser,
    TraitCategoryClass,
    MacroTrait,
    RollStatistic,
    RollProbability,
]


def _create_test_database_data():
    """Create test data for use in tests."""
    DatabaseVersion.create(version="1.0.0")
    Guild.create(id=1, name="test_guild", data={"key": "value"})
    Guild.create(id=2, name="test_guild2", data={"key": "value"})
    User.create(id=1, username="test_user", name="Test User")
    GuildUser.create(guild=1, user=1)
    Character.create(
        guild=1,
        created_by=1,
        clan=1,
        char_class=1,
        data={
            "first_name": "test",
            "last_name": "character",
            "nickname": "testy",
        },
    )
    TraitValue.create(character=1, trait=1, value=1)
    TraitValue.create(character=1, trait=2, value=2)
    TraitValue.create(character=1, trait=3, value=3)
    CustomTrait.create(
        character=1,
        guild=1,
        name="Test_Trait",
        category=13,
        value=2,
        max_value=5,
    )


@pytest.fixture(scope="class")
def mock_db() -> CSqliteExtDatabase:
    """Create a mock database with test data for use in tests.

    The database is bound to the models, then populated with test data.
    At the end of the test, the database is closed.

    Yields:
        CSqliteExtDatabase: The mock database.
    """
    test_db = CSqliteExtDatabase(":memory:")
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(MODELS)
    PopulateDatabase(test_db).populate()

    _create_test_database_data()  # Create test data

    # Confirm test data was created
    assert Guild.get_by_id(1).name == "test_guild"
    assert User.get_by_id(1).username == "test_user"
    assert CharacterClass.get_by_id(1).name == "Mortal"
    assert VampireClan.get_by_id(1).name == "Assamite"
    assert Character.get_by_id(1).data["first_name"] == "test"
    assert CustomTrait.get_by_id(1).name == "Test_Trait"
    # assert CustomSection.get_by_id(1).title == "test_section"
    assert GuildUser.get_by_id(1).guild.name == "test_guild"
    # assert Macro.get_by_id(1).name == "test_macro"
    assert TraitValue.get_by_id(1).value == 1
    assert TraitValue.get_by_id(2).value == 2
    assert TraitValue.get_by_id(3).value == 3

    yield test_db

    test_db.close()


@pytest.fixture(scope="class")
def empty_db() -> CSqliteExtDatabase:
    """Create an empty database for use in tests.

    The database is bound to the models but not populated with any data.
    At the end of the test, the database is closed.

    Yields:
        CSqliteExtDatabase: The empty database.
    """
    empty_db = CSqliteExtDatabase(":memory:")
    empty_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    empty_db.connect()
    empty_db.create_tables(MODELS)
    yield empty_db
    empty_db.close()


### Mock Objects ################################
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

    mock_member = mocker.MagicMock()
    mock_member.id = 2
    mock_member.display_name = "Test User2"
    mock_member.name = "testuser2"
    mock_member.mention = "<@2>"
    mock_member.__class__ = discord.Member
    mock_member.roles = [mock_role_one, mock_role_two]

    return mock_member


@pytest.fixture()
def mock_ctx(mocker, mock_member):
    """Create a mock context object with user 1."""
    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.user_svc.update_or_add_user = MagicMock(return_value=mock_member)
    mock_bot.__class__ = commands.Bot

    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 1
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.author = mock_member
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture()
def mock_ctx2(mocker, mock_member):
    """Create a mock context object with guild 2."""
    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot
    mock_bot.user_svc.update_or_add_user = MagicMock(return_value=mock_member)

    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 2
    mock_guild.name = "Test Guild2"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.author = mock_member
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture()
def mock_ctx3(mocker):
    """Create a mock context object with user not in the database."""
    # Mock the ctx.author object to match the mock database
    mock_author = mocker.MagicMock()
    mock_author.id = 600
    mock_author.display_name = "Test User 600"
    mock_author.name = "testuser 600"
    mock_author.mention = "<@600>"
    mock_author.__class__ = discord.Member

    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot
    mock_bot.user_svc.update_or_add_user = MagicMock(return_value=mock_author)

    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 1
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.author = mock_author
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture()
def mock_ctx4(mocker):
    """Create a mock context object with user AND a guild not in the database."""
    # Mock the ctx.author object
    mock_author = mocker.MagicMock()
    mock_author.id = 500
    mock_author.display_name = "Test User 500"
    mock_author.name = "testuser 500"
    mock_author.mention = "<@500>"
    mock_author.__class__ = discord.Member

    # Mock the ctx.bot object
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot
    mock_bot.user_svc.update_or_add_user = MagicMock(return_value=mock_author)

    # Mock the ctx.guild object
    mock_guild = mocker.MagicMock()
    mock_guild.id = 500
    mock_guild.name = "Test Guild 500"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.author = mock_author
    mock_ctx.bot = mock_bot
    mock_ctx.guild = mock_guild
    mock_ctx.__class__ = discord.ApplicationContext

    return mock_ctx


@pytest.fixture()
def mock_autocomplete_ctx1(mocker):
    """Create a mock autocomplete context object with user 1."""
    # Mock the ctx.guild object matches the mock database
    mock_guild = mocker.MagicMock()
    mock_guild.id = 1
    mock_guild.name = "Test Guild"
    mock_guild.data = {"key": "value"}
    mock_guild.__class__ = discord.Guild

    mock_user = mocker.MagicMock()
    mock_user.id = 1

    mock_interaction = mocker.MagicMock()
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_user

    # Mock the ctx object
    mock_ctx = mocker.MagicMock()
    mock_ctx.interaction = mock_interaction

    mock_ctx.__class__ = discord.AutocompleteContext

    return mock_ctx


### OTHER FIXTURES ################################
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
