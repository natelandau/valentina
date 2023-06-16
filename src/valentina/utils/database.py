"""Helper functions for managing the database."""
from datetime import datetime, timezone

from loguru import logger
from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate

from valentina import DATABASE
from valentina.models import (
    Character,
    CharacterClass,
    CustomTrait,
    Guild,
    GuildUser,
    User,
    UserCharacter,
)
from valentina.models.constants import GROUPED_TRAITS, CharClass
from valentina.utils.helpers import normalize_row


def create_tables() -> None:
    """Create the database instance and tables."""
    with DATABASE:
        DATABASE.create_tables(
            [Guild, CharacterClass, Character, CustomTrait, User, GuildUser, UserCharacter]
        )

    logger.info("DATABASE: Create Tables")
    populate_enum_tables()


def populate_enum_tables() -> None:
    """Populate the database with enums."""
    for char_class in CharClass:
        CharacterClass.get_or_create(name=char_class.value)
    logger.info("DATABASE: Populate Enums")


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


def update_guild_last_connected(guild_id: int, guild_name: str) -> None:
    """Update the last connected timestamp for a guild."""
    db_id, is_created = Guild.get_or_create(
        id=guild_id,
        defaults={
            "id": guild_id,
            "name": guild_name,
            "first_seen": datetime.now(timezone.utc).replace(microsecond=0),
            "last_connected": datetime.now(timezone.utc).replace(microsecond=0),
        },
    )
    if is_created:
        logger.info(f"DATABASE: Create guild {db_id.name}")
    if not is_created:
        Guild.set_by_id(
            db_id, {"last_connected": datetime.now(timezone.utc).replace(microsecond=0)}
        )
        logger.info(f"DATABASE: Update '{db_id.name}'")


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
                    logger.info(f"DATABASE: Add row '{normalize_row(trait)}' to 'character' table.")
                    migrate(
                        migrator.add_column(
                            "character", normalize_row(trait), IntegerField(default=0)
                        )
                    )
