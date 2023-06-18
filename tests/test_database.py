# type: ignore
"""Test the database services."""

from peewee import SqliteDatabase

from valentina.models.database import (
    Character,
    CharacterClass,
    CustomTrait,
    DiceBinding,
    Guild,
    GuildUser,
    User,
    UserCharacter,
)
from valentina.models.database_services import DatabaseService

MODELS = [
    Guild,
    CharacterClass,
    Character,
    CustomTrait,
    User,
    GuildUser,
    UserCharacter,
    DiceBinding,
]


def test_create_tables(tmp_path):
    """Test that the tables are created."""
    db_path = tmp_path / "test.db"
    test_db = SqliteDatabase(db_path)
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)

    DatabaseService(test_db).create_new_db()
    assert test_db.table_exists("guild")
    assert test_db.table_exists("character")
    assert CharacterClass.get_by_id(1).name == "Mortal"
