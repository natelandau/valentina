# type: ignore
"""Shared fixtures for database tests.

This file contains fixtures that are used by multiple database tests.

mock_db: A mock database with test data for use in tests. Any changes made to this database will persist between tests.

empty_db: A database with tables but no data for use in tests. Any changes made to this database will not persist between tests.

"""
import discord
import peewee as pw
import pytest

from valentina.models.database import (
    Character,
    CharacterClass,
    CustomCharSection,
    CustomTrait,
    DatabaseVersion,
    Guild,
    GuildUser,
    Macro,
    User,
    VampireClan,
)

# IMPORTANT: This list must be kept in sync with all the models defined in src/valentina/models/database.py
MODELS = [
    Character,
    CharacterClass,
    CustomCharSection,
    CustomTrait,
    DatabaseVersion,
    Guild,
    GuildUser,
    Macro,
    User,
    VampireClan,
]

databaseversion = {"version": "1.0.0"}
guild = {"id": 1, "name": "test_guild"}
user = {"id": 1, "username": "test_user", "name": "Test User"}
characterclass = {"name": "test_class"}
vampireclan = {"name": "test_clan"}
character = {
    "first_name": "test",
    "last_name": "character",
    "nickname": "testy",
    "char_class": 1,
    "guild": 1,
    "created_by": 1,
    "clan": 1,
}
customtrait = {
    "character": 1,
    "guild": 1,
    "name": "test_trait",
    "category": "test_category",
    "value": 2,
    "max_value": 5,
}
customcharsection = {
    "character": 1,
    "guild": 1,
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


@pytest.fixture(scope="class")
def mock_db() -> pw.SqliteDatabase:
    """Create a mock database with test data for use in tests."""
    full_db = pw.SqliteDatabase(":memory:")
    full_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    full_db.connect()
    full_db.create_tables(MODELS)

    # Create test data
    DatabaseVersion.create(**databaseversion)
    Guild.create(**guild)
    User.create(**user)
    CharacterClass.create(**characterclass)
    VampireClan.create(**vampireclan)
    Character.create(**character)
    CustomTrait.create(**customtrait)
    CustomCharSection.create(**customcharsection)
    GuildUser.create(**guilduser)
    Macro.create(**macro)

    # Confirm test data was created
    assert Guild.get_by_id(1).name == "test_guild"
    assert User.get_by_id(1).username == "test_user"
    assert CharacterClass.get_by_id(1).name == "test_class"
    assert VampireClan.get_by_id(1).name == "test_clan"
    assert Character.get_by_id(1).first_name == "test"
    assert CustomTrait.get_by_id(1).name == "test_trait"
    assert CustomCharSection.get_by_id(1).title == "test_section"
    assert GuildUser.get_by_id(1).guild.name == "test_guild"
    assert Macro.get_by_id(1).name == "test_macro"

    yield full_db

    full_db.close()


@pytest.fixture()
def empty_db() -> pw.SqliteDatabase:
    """Create an empty database for use in tests."""
    empty_db = pw.SqliteDatabase(":memory:")
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


@pytest.fixture()
def ctx_existing():
    """Create a mock context object containing object in the mock database."""
    mock_guild = MockGuild(1, "Test Guild")
    mock_user = MockUser(1, "Test User", "testuser", "<@1>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def ctx_new_user():
    """Create a mock context object that has a user not in the mock database."""
    mock_guild = MockGuild(1, "Test Guild")
    mock_user = MockUser(2, "Test User 2", "testuser 2", "<@2>")
    return MockCTX(mock_guild, mock_user)


@pytest.fixture()
def ctx_new_user_guild():
    """Create a mock context object that has a user and a guild not in the mock database."""
    mock_guild = MockGuild(2, "Test Guild 2")
    mock_user = MockUser(2, "Test User 2", "testuser 2", "<@2>")
    return MockCTX(mock_guild, mock_user)
