"""Classes for managing the database."""
from os import DirEntry
from pathlib import Path

import aiofiles.os
import arrow
import inflect
from loguru import logger
from playhouse.sqlite_ext import CSqliteExtDatabase

from valentina.models.sqlite_models import (
    DATABASE,
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
    VampireClan,
)

p = inflect.engine()


class DatabaseService:
    """Services for managing the database and working with miscellaneous data."""

    def __init__(self, database: CSqliteExtDatabase) -> None:
        """Initialize DatabaseService with the provided Peewee database instance.

        Args:
            database (CSqliteExtDatabase): The Peewee database instance.
        """
        self.db = database

    @staticmethod
    async def backup_database(config: dict) -> Path:
        """Create a backup of the database and clean old backups.

        This method initializes a DBBackup instance to create a new backup
        of the database. After that, it cleans up older backups.

        Args:
            config (dict): Configuration dictionary for the backup process.

        Returns:
            Path: The path to the created backup file.

        """
        db_backup = DBBackup(config, DATABASE)
        backup_file = await db_backup.create_backup()
        await db_backup.clean_old_backups()
        return backup_file

    def _create_tables(self) -> None:
        """Create tables in the database if they do not exist."""
        logger.debug("DATABASE: Begin create Tables")
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
            )
        logger.info("DATABASE: Create Tables")

    @staticmethod
    def fetch_current_version() -> str:
        """Fetch the latest version of the database.

        Returns:
            str: The latest database version.
        """
        return DatabaseVersion.select().order_by(DatabaseVersion.id.desc()).get().version

    def _column_exists(self, table: str, column: str) -> bool:
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

    def _get_tables(self) -> list[str]:
        """Get all tables in the Database."""
        with self.db:
            cursor = self.db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cursor.fetchall()]

    def perform_database_migration(self, bot_version: str) -> None:
        """Migrate the database before populating it. This method should only be called when a database migration must be performed before populating the database."""
        # Confirm there is a database version column
        if not self._get_tables() or not self._column_exists("databaseversion", "version"):
            logger.info("DATABASE: New database, skip migration")
            return

        # Fetch the current database version
        current_db_version = self.fetch_current_version()

        # Migrate the database
        # # MigrateDatabase(
        #     self.db,
        #     bot_version=bot_version,
        #     db_version=current_db_version,
        # ).migrate()

    def initialize_database(self, bot_version: str) -> None:
        """Populate the database with initial data and update the database version.

        Populate the database first. Then, either create a new database with the current bot version

        Args:
            bot_version (str): Current version of the bot.

        Returns:
            None
        """
        # Perform any database migrations before populating the database, if a database exists
        self.perform_database_migration(bot_version)

        # Create tables if they do not exist
        self._create_tables()

        # Populate the database with up-to-date data
        # PopulateDatabase(self.db).populate()

        # Check or create the database version
        _, new_db_created = DatabaseVersion.get_or_create(
            defaults={"version": bot_version},
        )

        if new_db_created:
            # Log database creation if a new one is created, then return
            logger.info(f"DATABASE: Create new database v{bot_version}")
            return

        # Fetch current database version
        current_db_version = self.fetch_current_version()

        # Update the database version
        if current_db_version != bot_version:
            DatabaseVersion.create(version=bot_version)

        logger.info(f"DATABASE: Database is v{bot_version}")


class DBBackup:
    """A class that manages backups of the bot database.

    This class handles operations like determining the backup type (hourly, daily, weekly, monthly, or yearly), creating the backup, and cleaning old backups based on retention policies.

    Attributes:
        retention_daily (int): The retention policy for daily backups.
        retention_weekly (int): The retention policy for weekly backups.
        retention_monthly (int): The retention policy for monthly backups.
        retention_yearly (int): The retention policy for yearly backups.
        db_path (Path): The path to the database.
        backup_dir (Path): The directory where backups are stored.
        db (CSqliteExtDatabase): The database to backup.
    """

    def __init__(self, config: dict, db: CSqliteExtDatabase) -> None:
        """Initialize DBBackup class.

        Args:
            config (Config): A dictionary containing configuration values.
            db (CSqliteExtDatabase): The database to backup.

        """
        self.retention_daily = int(config.get("VALENTINA_DAILY_RETENTION", 1))
        self.retention_weekly = int(config.get("VALENTINA_WEEKLY_RETENTION", 1))
        self.retention_monthly = int(config.get("VALENTINA_MONTHLY_RETENTION", 1))
        self.retention_yearly = int(config.get("VALENTINA_YEARLY_RETENTION", 1))
        self.db_path = Path(config.get("VALENTINA_DB_PATH", "/valentina/db"))
        self.backup_dir = Path(config.get("VALENTINA_BACKUP_PATH", "/valentina/backup"))
        self.db = db

    @staticmethod
    def type_of_backup() -> str:
        """Determine the type of backup to perform.

        Determine whether the backup type should be "yearly", "monthly", "weekly", or "daily" based on the current date.

        Returns:
            str: The type of backup to perform.
        """
        now = arrow.utcnow()
        today = now.format("YYYY-MM-DD")
        yearly = now.span("year")[0].format("YYYY-MM-DD")
        monthly = now.span("month")[0].format("YYYY-MM-DD")

        if today == yearly:
            return "yearly"
        if today == monthly:
            return "monthly"
        if now.weekday() == 0:  # Monday is denoted by 0
            return "weekly"

        return "daily"

    async def create_backup(self) -> Path:
        """Create a backup of the database.

        To accomplish a comprehensive backup, do the following:

        1. Close the existing database connection to ensure data integrity.
        2. Determine the type of backup (e.g., daily, weekly) using custom logic.
        3. Create required directories asynchronously for backup storage.
        4. Generate a unique backup file name using the current date, time, and backup type.
        5. Perform a database backup to the specified file.
        6. Log key actions for debugging or auditing purposes.
        7. Reconnect to the database for continued operations.

        Returns:
            Path: Return a `Path` object indicating the location of the backup file on disk.
        """
        # Close the database connection to ensure that the backup contains all the data
        self.db.close()

        backup_type = self.type_of_backup()

        await aiofiles.os.makedirs(self.backup_dir, exist_ok=True)

        backup_file = (
            self.backup_dir / f"{arrow.utcnow().format('YYYY-MM-DDTHHmmss')}-{backup_type}.sqlite"
        )

        self.db.backup_to_file(backup_file)

        logger.info(f"BACKUP: {backup_type} database backup")
        logger.debug(f"BACKUP: Create {backup_file}")

        # Reopen the database connection
        self.db.connect(reuse_if_open=True)

        return backup_file

    async def clean_old_backups(self) -> int:
        """Clean up old backups based on retention policies and return the count of deleted files.

        The method proceeds with the following steps:
        1. Scans the backup directory.
        2. Classifies each backup file based on its backup type (daily, weekly, etc.).
        3. Checks each category of backup against its respective retention policy.
        4. Deletes any backups that exceed the retention limit.
        5. Logs each deletion and the total number of deletions.

        Returns:
            int: The number of deleted files.
        """
        deleted = 0
        backups: dict[str, list[DirEntry[str]]] = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "yearly": [],
        }

        files = await aiofiles.os.scandir(self.backup_dir)

        for file in sorted(files, key=lambda x: x.name, reverse=True):
            for backup_type in backups:
                if backup_type in file.name:
                    backups[backup_type].append(file)

        for backup_type in backups:
            retention_policy = getattr(self, f"retention_{backup_type}")
            if len(backups[backup_type]) > retention_policy:
                for backup in backups[backup_type][retention_policy:]:
                    logger.debug(f"BACKUP: Delete {backup.name}")
                    await aiofiles.os.remove(backup)
                    deleted += 1

        logger.info(f"BACKUP: Delete {deleted} old db {p.plural_noun('backup', deleted)}")
        return deleted
