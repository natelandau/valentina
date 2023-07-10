"""Backup the bot database."""

from os import DirEntry
from pathlib import Path

import aiofiles.os
import arrow
from loguru import logger


class DBBackup:
    """Class to backup the bot database."""

    def __init__(self, config: dict) -> None:
        self.retention_daily = int(config["VALENTINA_DAILY_RETENTION"])
        self.retention_weekly = int(config["VALENTINA_WEEKLY_RETENTION"])
        self.retention_monthly = int(config["VALENTINA_MONTHLY_RETENTION"])
        self.retention_yearly = int(config["VALENTINA_YEARLY_RETENTION"])
        self.db_path = Path(config["VALENTINA_DB_PATH"])
        self.backup_dir = Path(config["VALENTINA_BACKUP_PATH"])

    def type_of_backup(self) -> str:
        """Determine the type of backup to perform.

        types: hourly, daily, weekly, monthly, yearly

        Returns:
            str: The type of backup to perform.
        """
        today = arrow.utcnow().format("YYYY-MM-DD")
        yearly = arrow.utcnow().span("year")[0].format("YYYY-MM-DD")
        monthly = arrow.utcnow().span("month")[0].format("YYYY-MM-DD")

        if today == yearly:
            return "yearly"
        if today == monthly:
            return "monthly"
        if arrow.utcnow().weekday() == 0:
            return "weekly"

        return "daily"

    async def create_backup(self) -> None:
        """Perform the backup."""
        backup_type = self.type_of_backup()

        await aiofiles.os.makedirs(self.backup_dir, exist_ok=True)

        backup_file = (
            self.backup_dir / f"{arrow.now().format('YYYY-MM-DDTHHmmss')}-{backup_type}.sqlite"
        )

        async with aiofiles.open(self.db_path, mode="rb") as source_file, aiofiles.open(
            backup_file, mode="wb"
        ) as dest_file:
            while True:
                chunk = await source_file.read(1024)
                if not chunk:
                    break
                await dest_file.write(chunk)

        logger.info(f"BACKUP: {backup_type} database backup complete")

    async def clean_old_backups(self) -> int:
        """Cleans old backups based off the retention policies. Returns the number of files deleted."""
        deleted = 0
        backups: dict[str, list[DirEntry[str]]] = {}

        files = await aiofiles.os.scandir(self.backup_dir)

        backups = {"daily": [], "weekly": [], "monthly": [], "yearly": []}

        for file in sorted(files, key=lambda x: x.name, reverse=True):
            for backup_type in backups:
                if backup_type in file.name:
                    backups[backup_type].append(file)

        for backup_type, _backup_list in backups.items():
            retention_policy = getattr(self, f"retention_{backup_type}")
            if len(backups[backup_type]) > retention_policy:
                for backup in backups[backup_type][retention_policy:]:
                    logger.debug(f"BACKUP: Deleting old backup: {backup.name}")
                    await aiofiles.os.remove(backup)
                    deleted += 1

        logger.info(f"BACKUP: old database backups deleted: {deleted}")
        return deleted
