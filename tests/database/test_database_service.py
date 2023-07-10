# type: ignore
"""Test working with new databases and the DatabaseService class."""
import peewee as pw
import pytest

from valentina.models.database import CharacterClass, DatabaseVersion, VampireClan
from valentina.models.database_services import DatabaseService

from .conftest import MODELS


def test_create_tables(tmp_path):
    """Test that the tables are created.

    GIVEN a completely empty database
    WHEN DatabaseService.create_tables() is called
    THEN the tables are created
    """
    db_path = tmp_path / "test.db"
    test_db = pw.SqliteDatabase(db_path)
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()

    DatabaseService(test_db).create_tables()
    assert test_db.table_exists("guilds")
    assert test_db.table_exists("characters")
    test_db.close()


def test_get_tables(mock_db):
    """Test DatabaseService.get_tables().

    GIVEN a database
    WHEN DatabaseService.get_tables() is called
    THEN the list of tables is returned
    """
    tables = DatabaseService(mock_db).get_tables()
    assert len(tables) == 17
    assert "characters" in tables


def test_sync_enums(empty_db):
    """Test DatabaseService.sync_enums().

    GIVEN a database
    WHEN DatabaseService.sync_enums() is called
    THEN the enums are synced
    """
    from valentina.models.constants import CharClass, VampClanList

    DatabaseService(empty_db).sync_enums()

    values = [x.value for x in CharClass]
    assert CharacterClass.get_by_id(1).name == values[0]
    assert CharacterClass.get_by_id(2).name == values[1]

    values = [x.value for x in VampClanList]
    assert VampireClan.get_by_id(1).name == values[0]
    assert VampireClan.get_by_id(2).name == values[1]


def test_requires_migration_one(empty_db):
    """Test DatabaseService.requires_migration().

    GIVEN an empty database
    WHEN DatabaseService.requires_migration() is called
    THEN True is returned and the database version is set
    """
    assert DatabaseService(empty_db).requires_migration("2.3.2") is False
    assert DatabaseVersion.get_by_id(1).version == "2.3.2"


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.1.0", False),
        ("1.0.0", False),
        ("1.0.1", True),
        ("2.3.3", True),
    ],
)
def test_requires_migration_two(mock_db, version, expected):
    """Test DatabaseService.requires_migration().

    GIVEN a database with a version
    WHEN DatabaseService.requires_migration() is called
    THEN the correct value is passed
    """
    print(DatabaseVersion.get_by_id(1).version)
    assert DatabaseService(mock_db).requires_migration(version) is expected
