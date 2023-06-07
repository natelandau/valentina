"""Helper functions for managing the database."""
from loguru import logger

from valentina import DATABASE
from valentina.models import Character, CharacterClass, Guild
from valentina.models.constants import CharClass


def create_tables() -> None:
    """Create the database instance and tables."""
    with DATABASE:
        DATABASE.create_tables([Guild, CharacterClass, Character])

    logger.info("DATABASE: Tables created successfully.")
    populate_enum_tables()


def populate_enum_tables() -> None:
    """Populate the database with enums."""
    for char_class in CharClass:
        CharacterClass.get_or_create(name=char_class.value)
    logger.info("DATABASE: Enums populated successfully.")
