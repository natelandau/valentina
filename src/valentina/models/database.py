"""Classes for managing the database."""
from pathlib import Path

from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models.db_tables import (
    DATABASE,
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
    RollThumbnail,
    Trait,
    TraitCategory,
    TraitCategoryClass,
    TraitClass,
    TraitValue,
    User,
    VampireClan,
)
from valentina.utils.db_backup import DBBackup
from valentina.utils.db_initialize import MigrateDatabase, PopulateDatabase


class DatabaseService:
    """Representation of the database."""

    def __init__(self, database: CSqliteExtDatabase) -> None:
        """Initialize the DatabaseService."""
        self.db = database

    @staticmethod
    async def backup_database(config: dict) -> Path:
        """Create a backup of the database."""
        backup_file = await DBBackup(config, DATABASE).create_backup()
        await DBBackup(config, DATABASE).clean_old_backups()
        return backup_file

    def column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table.

        Args:
            table (str): The table to check.
            column (str): The column to check.

        Returns:
            bool: Whether the column exists in the table.
        """
        db = self.db
        cursor = db.execute_sql(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    def create_tables(self) -> None:
        """Create all tables in the database if they don't exist."""
        with self.db:
            self.db.create_tables(
                [
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
                ]
            )
        logger.info("DATABASE: Create Tables")

    def get_tables(self) -> list[str]:
        """Get all tables in the Database."""
        with self.db:
            cursor = self.db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cursor.fetchall()]

    def database_version(self) -> str:
        """Get the version of the database."""
        return DatabaseVersion.get_by_id(1).version

    @logger.catch
    def initialize_database(self, bot_version: str) -> None:
        """Migrate from old database versions to the current one."""
        PopulateDatabase(self.db).populate()

        existing_data, new_db_created = DatabaseVersion.get_or_create(
            id=1,
            defaults={"version": bot_version},
        )

        # If we are creating a new database, populate the necessary tables with data
        if new_db_created:
            logger.info(f"DATABASE: Create version v{bot_version}")
            return

        # If database exists, perform migrations if necessary
        MigrateDatabase(
            self.db,
            bot_version=bot_version,
            db_version=existing_data.version,
        ).migrate()

        # Bump the database version to the latest bot version
        DatabaseVersion.set_by_id(1, {"version": bot_version})
        logger.info(f"DATABASE: Database running v{bot_version}")
