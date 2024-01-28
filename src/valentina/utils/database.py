"""Database utilities for Valentina."""

import pymongo
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
from valentina.utils import ValentinaConfig


def test_db_connection() -> bool:
    """Test the database connection using pymongo."""
    logger.debug("DB: Testing connection...")
    mongo_uri = ValentinaConfig().mongo_uri

    try:
        client: pymongo.MongoClient = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1800)
        client.server_info()
        logger.info("DB: Connection successful")
    except pymongo.errors.ServerSelectionTimeoutError:
        return False
    else:
        return True


async def init_database(client=None, database=None) -> None:  # type: ignore [no-untyped-def]
    """Initialize the database. If a client is not provided, one will be created.

    Args:
        client (AsyncIOMotorClient, optional): The database client. Defaults to None.
        database (AsyncIOMotorClient, optional): The database. Defaults to None.
    """
    logger.debug("DB: Initializing...")
    mongo_uri = ValentinaConfig().mongo_uri
    db_name = ValentinaConfig().mongo_database_name

    # Create Motor client
    if not client:
        client = AsyncIOMotorClient(f"{mongo_uri}", tz_aware=True, serverSelectionTimeoutMS=1800)

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
