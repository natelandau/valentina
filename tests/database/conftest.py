"""Shared fixtures for database tests.

This file contains fixtures that are used by multiple database tests.

mock_db: A mock database with test data for use in tests. Any changes made to this database will persist between tests.

empty_db: A database with tables but no data for use in tests. Any changes made to this database will not persist between tests.

"""

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


@pytest.fixture()
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
