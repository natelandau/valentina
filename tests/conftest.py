# type: ignore
"""Shared fixtures for database tests.

This module contains shared fixtures that are used by multiple database tests.

Fixtures:
    mock_db: A mock database with test data for use in tests.
    empty_db: A database with no data for use in tests.
    ctx: A context object with an existing user.
    ctx_new_user: A context object with a new user.
    ctx_new_user_guild: A context object with a new user and a new guild.
    existing_character: A character object that exists in the mock database.
    caplog: Overwrite the built-in caplog fixture to capture loguru logs.
"""
import logging

import discord
import pytest
from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models.db_tables import (
    Character,
    CharacterClass,
    Chronicle,
    ChronicleChapter,
    ChronicleNote,
    ChronicleNPC,
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
    Chronicle,
    ChronicleNote,
    ChronicleChapter,
    ChronicleNPC,
    Trait,
    TraitClass,
    TraitValue,
    GuildUser,
    TraitCategoryClass,
    MacroTrait,
    RollStatistic,
    RollProbability,
]

databaseversion = {"version": "1.0.0"}
guild = {"id": 1, "name": "test_guild", "data": {"key": "value"}}
guild2 = {"id": 2, "name": "test_guild2", "data": {"key": "value"}}
user1 = {"id": 1, "username": "test_user", "name": "Test User"}
user22 = {"id": 22, "username": "test_user22", "name": "Test User22"}
character1 = {
    "first_name": "test",
    "last_name": "character",
    "nickname": "testy",
    "char_class": 1,
    "guild": 1,
    "created_by": 1,
    "clan": 1,
    "strength": 5,
    "willpower": 5,
}
character2 = {
    "first_name": "test2",
    "last_name": "character2",
    "nickname": "testy2",
    "char_class": 1,
    "guild": 1,
    "created_by": 1,
    "clan": 1,
    "strength": 5,
    "willpower": 5,
}

custom_section = {
    "character": 1,
    "title": "test_section",
    "description": "test_description",
}
guilduser = {"guild": 1, "user": 1}
macro = {
    "guild": 1,
    "user": 1,
    "name": "test_macro",
    "abbreviation": "tm",
    "description": "test description",
    "content": "test_content",
    "trait_one": "test_trait_one",
    "trait_two": "test_trait_two",
}
trait_values1 = {"character_id": 1, "trait_id": 1, "value": 1}
trait_values2 = {"character_id": 1, "trait_id": 2, "value": 2}
trait_values3 = {"character_id": 1, "trait_id": 3, "value": 3}
trait_category = {"name": 1}


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

    # Create test data

    DatabaseVersion.create(**databaseversion)
    Guild.create(**guild)
    Guild.create(**guild2)
    User.create(**user1)
    User.create(**user22)
    Character.create(**character1)
    Character.create(**character2)

    customtrait = {
        "character": 1,
        "guild": 1,
        "name": "Test_Trait",
        "category": TraitCategory.get(name="Skills"),
        "value": 2,
        "max_value": 5,
    }
    CustomTrait.create(**customtrait)
    CustomSection.create(**custom_section)
    GuildUser.create(**guilduser)
    Macro.create(**macro)
    TraitCategory.create(**trait_category)
    TraitValue.create(**trait_values1)
    TraitValue.create(**trait_values2)
    TraitValue.create(**trait_values3)

    # Confirm test data was created
    assert Guild.get_by_id(1).name == "test_guild"
    assert User.get_by_id(1).username == "test_user"
    assert CharacterClass.get_by_id(1).name == "Mortal"
    assert VampireClan.get_by_id(1).name == "Assamite"
    assert Character.get_by_id(1).first_name == "test"
    assert CustomTrait.get_by_id(1).name == "Test_Trait"
    assert CustomSection.get_by_id(1).title == "test_section"
    assert GuildUser.get_by_id(1).guild.name == "test_guild"
    assert Macro.get_by_id(1).name == "test_macro"
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
class MockGuild(discord.Guild):
    """Mock guild object."""

    def __init__(self, id, name: str | None = None):
        self.id = id
        self.name = name
        self.data = {"key": "value"}


class MockUser:
    """Mock user object."""

    def __init__(self, id, display_name, name, mention):
        self.id = id
        self.display_name = display_name
        self.name = name
        self.mention = mention


class MockCTX(discord.ApplicationContext):
    """Mock context object."""

    def __init__(self, guild, author):
        self.guild = guild
        self.author = author


class MockCharacter:
    """Mock character object."""

    def __init__(self, id, first_name, last_name):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.name = f"{first_name} {last_name}"
        self.guild = 1
        self.created_by = 1
        self.class_name = "test_class"


class MockTrait:
    """Mock trait object."""

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.category = 1


@pytest.fixture()
def mock_ctx():
    """Create a mock context object containing object in the mock database."""
    mock_guild = MockGuild(1, "Test Guild")
    mock_user = MockUser(1, "Test User", "testuser", "<@1>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def mock_ctx2():
    """Create a mock context object containing object in the mock database."""
    mock_guild = MockGuild(2, "Test Guild2")
    mock_user = MockUser(1, "Test User", "testuser", "<@1>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def existing_user():
    """Create a mock user object."""
    return MockUser(1, "Test User 1", "testuser 1", "<@1>")


@pytest.fixture()
def ctx_new_user():
    """Create a mock context object that has a user not in the mock database."""
    mock_guild = MockGuild(1, "Test Guild")
    mock_user = MockUser(2, "Test User 2", "testuser 2", "<@2>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def ctx_new_user_guild():
    """Create a mock context object that has a user and a guild not in the mock database."""
    mock_guild = MockGuild(500, "Test Guild 500")
    mock_user = MockUser(500, "Test User 500", "testuser 500", "<@500>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def existing_character():
    """Create a mock character object that is in the mock database."""
    return MockCharacter(1, "first", "last")


@pytest.fixture()
def existing_trait():
    """Create a mock trait object that is in the mock database."""
    return MockTrait(1, "test_trait")


@pytest.fixture()
def caplog(caplog):
    """Override and wrap the caplog fixture with one of our own. This fixes a problem where loguru logs could not be captured by caplog."""
    logger.remove()  # remove default handler, if it exists
    # logger.enable("")  # enable all logs from all modules
    # logging.addLevelName(5, "TRACE")  # tell python logging how to interpret TRACE logs

    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    logger.add(
        PropogateHandler(), format="{message}"
    )  # shunt logs into the standard python logging machinery
    # caplog.set_level(0)  # Tell logging to handle all log levels
    return caplog
