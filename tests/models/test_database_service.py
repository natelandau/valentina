# type: ignore
"""Test working with new databases and the DatabaseService class."""

from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models import DatabaseService
from valentina.models.db_tables import DatabaseVersion

from .conftest import MODELS


def test_create_tables(tmp_path):
    """Test that the tables are created.

    GIVEN a completely empty database
    WHEN DatabaseService.create_tables() is called
    THEN the tables are created
    """
    db_path = tmp_path / "test.db"
    test_db = CSqliteExtDatabase(db_path)
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()

    DatabaseService(test_db).create_tables()
    assert test_db.table_exists("guilds")
    assert test_db.table_exists("characters")
    test_db.close()


def test_initialize_database_one(empty_db):
    """Test DatabaseService.initialize_database().

    GIVEN an empty database
    WHEN DatabaseService.initialize_database() is called
    THEN the initial database version is set
    """
    DatabaseService(empty_db).initialize_database("2000.3.2")
    assert DatabaseVersion.get_by_id(1).version == "2000.3.2"