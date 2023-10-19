# type: ignore
"""Tests for mongodb."""

import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from valentina.models.mongo_collections import Guild


@pytest.mark.asyncio()
async def test_mock_client():
    collection = AsyncMongoMockClient()["tests"]["test-1"]

    assert await collection.find({}).to_list(None) == []

    result = await collection.insert_one({"a": 1})
    assert result.inserted_id

    assert len(await collection.find({}).to_list(None)) == 1


@pytest.mark.asyncio()
async def test_beanie() -> None:
    """Test beanie."""
    client = AsyncMongoMockClient(
        "mongodb://user:pass@host:00001", connectTimeoutMS=250, tz_aware=True
    )
    await init_beanie(database=client.beanie_test, document_models=[Guild])

    guild1 = Guild(id=1234567, name="test1")
    await guild1.insert()

    guild2 = Guild(id=987654321, name="test2")
    await guild2.insert()

    returned = await Guild.get(guild1.id)
    from rich import print

    print(guild1)
    print(returned)
    assert returned == guild1
