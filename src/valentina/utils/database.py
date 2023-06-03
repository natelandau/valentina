"""Utility functions for database operations."""


from loguru import logger

from valentina.models.database import Database


async def create_database(db: Database) -> bool:
    """Create the database instance and tables.

    Args:
        db (Database): The database instance.
    """
    # Create tables
    await db.execute(
        """CREATE TABLE IF NOT EXISTS "Guilds" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "guild_id" INTEGER NOT NULL,
                "name" TEXT NOT NULL,
                "created" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "last_connected" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    logger.info("DATABASE: Tables created successfully.")
    return True
