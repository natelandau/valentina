"""Models for the sqlite database."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger


class Database:
    """Class representing a sqlite database."""

    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path = db_path

    async def execute(self, sql_statement: str, *args: str) -> bool:
        """Execute a sql statement.

        Args:
            sql_statement (str): The sql statement to execute.
            *args (str): The arguments to pass to the sql statement.

        Returns:
            bool: Whether the sql statement was successful.
        """
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(sql_statement, args)
                await db.commit()
            except aiosqlite.Error as e:
                logger.error(e)
                success = False
            else:
                success = True

            return success

    async def fetch(self, sql_statement: str, *args: Any) -> Iterable[aiosqlite.Row]:
        """Fetch a sql statement.

        Args:
            sql_statement (str): The sql statement to execute.
            *args (str): The arguments to pass to the sql statement.

        Returns:
            Iterable[aiosqlite.Row]: The result of the sql statement.
        """
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(sql_statement, args)
                result = await cursor.fetchall()
            except aiosqlite.Error as e:
                logger.error(e)
                result = []

            return result

    async def insert(self, sql_statement: str, *args: Any) -> int | None:
        """Insert a sql statement.

        Args:
            sql_statement (str): The sql statement to execute.
            *args (str): The arguments to pass to the sql statement.

        Returns:
            int | None: The last row id of the sql statement.
        """
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(sql_statement, args)
                await db.commit()
                result = cursor.lastrowid
            except aiosqlite.Error as e:
                logger.error(e)
                result = None

            return result
