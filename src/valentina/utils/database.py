"""Database utilities for Valentina."""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from valentina.constants import CONFIG
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


async def init_database(client=None, database=None) -> None:  # type: ignore [no-untyped-def]
    """Initialize the database. If a client is not provided, one will be created.

    Args:
        client (AsyncIOMotorClient, optional): The database client. Defaults to None.
        database (AsyncIOMotorClient, optional): The database. Defaults to None.
    """
    # Create Motor client
    if not client:
        client = AsyncIOMotorClient(f"{CONFIG['VALENTINA_MONGO_URI']}", tz_aware=True)

    # Initialize beanie with the Sample document class and a database
    await init_beanie(
        database=database
        if database is not None
        else client[CONFIG["VALENTINA_MONGO_DATABASE_NAME"]],
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
