"""Database utilities for Valentina."""

from beanie import init_beanie
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from valentina.models import (
    Campaign,
    Character,
    CharacterTrait,
    GlobalProperty,
    Guild,
    RollProbability,
    RollStatistic,
    User,
)
from valentina.utils.helpers import get_config_value


async def init_database(client=None, database=None) -> None:  # type: ignore [no-untyped-def]
    """Initialize the database. If a client is not provided, one will be created.

    Args:
        client (AsyncIOMotorClient, optional): The database client. Defaults to None.
        database (AsyncIOMotorClient, optional): The database. Defaults to None.
    """
    logger.debug("DB: Initializing...")
    mongo_uri = get_config_value("VALENTINA_MONGO_URI")
    db_name = get_config_value("VALENTINA_MONGO_DATABASE_NAME")

    # Create Motor client
    if not client:
        client = AsyncIOMotorClient(f"{mongo_uri}", tz_aware=True)

    # Initialize beanie with the Sample document class and a database
    await init_beanie(
        database=database if database is not None else client[db_name],
        document_models=[
            Campaign,
            Character,
            CharacterTrait,
            GlobalProperty,
            RollStatistic,
            Guild,
            User,
            RollProbability,
        ],
    )

    logger.info("DB: Initialized")
