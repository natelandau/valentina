"""Classes for managing the database."""
from os import DirEntry
from pathlib import Path

import aiofiles.os
import arrow
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
from valentina.utils.db_initialize import MigrateDatabase, PopulateDatabase
from valentina.utils.helpers import pluralize


class DatabaseService:
    """Services for managing the database and working with miscellaneous data."""

    def __init__(self, database: CSqliteExtDatabase) -> None:
        """Initialize the DatabaseService."""
        self.db = database

    @staticmethod
    async def backup_database(config: dict) -> Path:
        """Create a backup of the database."""
        backup_file = await DBBackup(config, DATABASE).create_backup()
        await DBBackup(config, DATABASE).clean_old_backups()
        return backup_file

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
                    RollStatistic,
                ]
            )
        logger.info("DATABASE: Create Tables")

    def fetch_database_version(self) -> str:
        """Get the version of the database."""
        return DatabaseVersion.get_by_id(1).version

    @logger.catch
    def initialize_database(self, bot_version: str) -> None:
        """Migrate old database versions to the current one.

        First, populate the database. Then, check the database's existence and version.
        If the database does not exist, create it. Otherwise, apply necessary migrations.

        Args:
            bot_version (str): The version of the bot running the script.

        Returns:
            None
        """
        # Populate the database
        PopulateDatabase(self.db).populate()

        database_version, new_db_created = DatabaseVersion.get_or_create(
            id=1,
            defaults={"version": bot_version},
        )

        if new_db_created:
            # Log database creation if a new one is created
            logger.info(f"DATABASE: Create new database v{bot_version}")
            return

        # Migrate existing database if needed
        MigrateDatabase(
            self.db,
            bot_version=bot_version,
            db_version=database_version.version,
        ).migrate()

        # Update the database version to the current bot version
        DatabaseVersion.set_by_id(1, {"version": bot_version})

        # Log the new version of the database
        logger.info(f"DATABASE: Database is v{bot_version}")

    def log_diceroll(self, fields: dict[str, str | int]) -> None:
        """Log a diceroll to the database."""
        RollStatistic.create(**fields)
        logger.debug(f"DATABASE: Create roll statistic: {fields}")


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

    def type_of_backup(self) -> str:
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
        """Create a database backup.

        The method does the following:
        1. Determines the type of backup (daily, weekly, etc.).
        2. Creates the necessary directories for storing the backup.
        3. Creates a backup file named according to the current date, time, and type of backup.
        4. Performs the database backup and stores it in the file.
        5. Logs the actions taken.

        Returns:
            Path: The path of the backup file.
        """
        backup_type = self.type_of_backup()

        await aiofiles.os.makedirs(self.backup_dir, exist_ok=True)

        backup_file = (
            self.backup_dir / f"{arrow.utcnow().format('YYYY-MM-DDTHHmmss')}-{backup_type}.sqlite"
        )

        self.db.backup_to_file(backup_file)

        logger.info(f"BACKUP: {backup_type} database backup")
        logger.debug(f"BACKUP: Create {backup_file}")
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

        for backup_type, _backup_list in backups.items():
            retention_policy = getattr(self, f"retention_{backup_type}")
            if len(backups[backup_type]) > retention_policy:
                for backup in backups[backup_type][retention_policy:]:
                    logger.debug(f"BACKUP: Delete {backup.name}")
                    await aiofiles.os.remove(backup)
                    deleted += 1

        logger.info(f"BACKUP: Delete {deleted} old db {pluralize(deleted, 'backup')}")
        return deleted
