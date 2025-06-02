"""Database utilities for Valentina."""

import pymongo
from beanie import init_beanie
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from valentina.models import (
    BrokerTask,
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    Character,
    CharacterTrait,
    DictionaryTerm,
    GlobalProperty,
    Guild,
    InventoryItem,
    Note,
    RollProbability,
    RollStatistic,
    User,
)
from valentina.utils import ValentinaConfig


def test_db_connection() -> bool:  # pragma: no cover
    """Test the database connection using pymongo.

    This function attempts to establish a connection to the MongoDB database
    using the configuration specified in ValentinaConfig. It uses a short
    timeout to quickly determine if the connection can be established.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
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


async def init_database(
    client: AsyncIOMotorClient | None = None,
    database: AsyncIOMotorDatabase | None = None,
) -> None:
    """Initialize the MongoDB database connection and configure Beanie ODM for document models.

    Connect to MongoDB using the provided client or create a new one with default configuration. Set up Beanie ODM with the application's document models for object-document mapping. Use an existing database instance or select one from the client based on configuration.

    Args:
        client (AsyncIOMotorClient | None): The existing database client to use. If None, create a new client with default settings. Defaults to None.
        database (AsyncIOMotorDatabase | None): The existing database instance to use. If None, select database from client using configured name. Defaults to None.
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
            BrokerTask,
            Campaign,
            CampaignBook,
            CampaignBookChapter,
            Character,
            CharacterTrait,
            DictionaryTerm,
            GlobalProperty,
            Guild,
            InventoryItem,
            Note,
            RollProbability,
            RollStatistic,
            User,
        ],
    )

    logger.info("DB: Initialized")
