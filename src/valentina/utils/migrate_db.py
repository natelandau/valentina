"""Helper functions for managing the database."""
from loguru import logger
from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate

from valentina import DATABASE
from valentina.models.constants import GROUPED_TRAITS
from valentina.utils.helpers import normalize_row


def column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table.

    Args:
        table (str): The table to check.
        column (str): The column to check.

    Returns:
        bool: Whether the column exists in the table.
    """
    db = DATABASE
    cursor = db.execute_sql(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


@logger.catch
def update_character_model() -> None:
    """Update the character table with all traits in GROUPED_TRAITS.

    Note that this will not update the Character model itself but is, instead, either:

        - a last resort for altering the database if changes were made and you forgot to add them to the model
        - a way to add custom traits to the database after the database is created.
    """
    db = DATABASE
    migrator = SqliteMigrator(db)

    for _group, categories in GROUPED_TRAITS.items():
        for _category, traits in categories.items():
            for trait in traits:
                if not column_exists("character", normalize_row(trait)):
                    logger.warning(
                        f"DATABASE: Add row '{normalize_row(trait)}' to 'character' table."
                    )
                    migrate(
                        migrator.add_column(
                            "character", normalize_row(trait), IntegerField(default=0)
                        )
                    )
