# type: ignore
"""Test the HTMX partials blueprint."""

from typing import Any

import pytest

from tests.factories import *
from valentina.models import (
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    Character,
    InventoryItem,
    Note,
    User,
)
from valentina.webui.constants import TableType


@pytest.fixture
async def test_setup(
    character_factory,
    mock_session,
    test_client,
    user_factory,
    guild_factory,
    campaign_factory,
    book_factory,
) -> tuple[Character, Campaign, User, CampaignBook, "TestClientProtocol"]:  # noqa: F405
    """Create base test environment."""
    guild = await guild_factory.build().insert()
    user = await user_factory.build(macros=[]).insert()
    character = await character_factory.build(guild=guild.id, inventory=[], notes=[]).insert()
    campaign = await campaign_factory.build(guild=guild.id, books=[], npcs=[], notes=[]).insert()
    book = await book_factory.build(campaign=str(campaign.id), chapters=[], notes=[]).insert()
    campaign.books.append(book)
    await campaign.save()

    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    return character, campaign, user, book, test_client


@pytest.mark.parametrize(
    ("table_type", "id_field", "parent_id_source"),
    [
        (TableType.NOTE, "note_id", "character"),
        (TableType.INVENTORYITEM, "item_id", "character"),
        (TableType.CHAPTER, "chapter_id", "book"),
        (TableType.NPC, "uuid", "campaign"),
        (TableType.MACRO, "uuid", "user"),
    ],
)
@pytest.mark.drop_db
async def test_form_load(test_setup, table_type, id_field, parent_id_source):
    """Test form load returns empty form."""
    character, campaign, user, book, test_client = test_setup

    # Dynamically get parent_id from either book or character based on table type
    # This allows us to test both chapter forms (which need book.id) and other forms (which need character.id)
    parent_id = locals()[parent_id_source].id
    # parent_id = campaign.id if table_type == TableType.NPC else parent_id

    url = f"/partials/table/{table_type.value.route_suffix}?parent_id={parent_id}"

    response = await test_client.put(url)
    returned_text = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'value="{parent_id}">' in returned_text

    assert f'<input id="{id_field}" name="{id_field}" type="hidden" value="">' in returned_text


@pytest.mark.parametrize(
    (
        "table_type",
        "model",
        "id_field",  # The field on the object that is its unique identifier. typically "id"
        "parent_object",
        "parent_id_field",  # Field on the target object that references it's parent id.
        "parent_link_field",  # Field on the parent object that is a list of target objects.
        "test_data",
        "update_data",
    ),
    [
        (
            TableType.NOTE,
            Note,
            "id",
            Character,
            "character_id",
            "notes",
            {"text": "test note"},
            {"text": "updated note"},
        ),
        (
            TableType.INVENTORYITEM,
            InventoryItem,
            "id",
            Character,
            "character_id",
            "inventory",
            {
                "name": "test item",
                "description": "test description",
                "type": "CONSUMABLE",
            },
            {
                "name": "updated item",
                "description": "updated description",
                "type": "CONSUMABLE",
            },
        ),
        (
            TableType.CHAPTER,
            CampaignBookChapter,
            "id",
            CampaignBook,
            "book_id",
            "chapters",
            {
                "name": "test chapter",
                "description_short": "test short description",
                "description_long": "test long description",
            },
            {
                "name": "test chapter updated",
                "description_short": "test short description updated",
                "description_long": "test long description updated",
            },
        ),
        (
            TableType.NPC,
            None,
            "uuid",
            Campaign,
            None,
            "npcs",
            {
                "name": "test name",
                "npc_class": "test class",
                "description": "test description",
            },
            {
                "name": "test name updated",
                "npc_class": "test class updated",
                "description": "test description updated",
            },
        ),
        (
            TableType.MACRO,
            None,
            "uuid",
            User,
            None,
            "macros",
            {
                "name": "test name",
                "abbreviation": "aaa",
                "description": "test description",
                "trait_one": "Strength",
                "trait_two": "Dexterity",
            },
            {
                "name": "test name updated",
                "abbreviation": "bbb",
                "description": "test description updated",
                "trait_one": "Strength",
                "trait_two": "Dexterity",
            },
        ),
    ],
)
@pytest.mark.drop_db
async def test_crud_operations(
    debug,
    test_setup,
    table_type,
    model,
    id_field,
    parent_object,
    parent_id_field,
    parent_link_field,
    test_data,
    update_data,
):
    """Test create, update, and delete operations."""
    character, campaign, user, book, test_client = test_setup
    base_url = f"/partials/table/{table_type.value.route_suffix}"

    # Get appropriate parent based on table type
    parent = (
        book
        if table_type == TableType.CHAPTER
        else campaign
        if table_type == TableType.NPC
        else user
        if table_type == TableType.MACRO
        else character
    )

    # Create
    create_data = {**test_data, parent_id_field: str(parent.id)} if parent_id_field else test_data

    response = await test_client.put(
        f"{base_url}?parent_id={parent.id}", json=create_data, follow_redirects=True
    )

    assert response.status_code == 200

    # Verify creation
    parent = await parent_object.get(parent.id, fetch_links=True)

    items = getattr(parent, parent_link_field)

    assert len(items) == 1
    item = items[0]
    item_id = getattr(item, id_field)

    # Get the created item's table row partial
    response = await test_client.get(
        f"{base_url}?item_id={item_id}&parent_id={parent.id}", follow_redirects=True
    )
    assert response.status_code == 200

    # Update
    update_data = {**update_data, "parent_id": str(parent.id)}
    response = await test_client.post(
        f"{base_url}?item_id={item_id}&parent_id={parent.id}",
        json=update_data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    # Delete
    response = await test_client.delete(
        f"{base_url}?item_id={item_id}&parent_id={parent.id}", follow_redirects=True
    )
    assert response.status_code == 200

    if model:
        assert await model.get(item_id) is None

    # Verify deletion
    parent = await parent_object.get(parent.id, fetch_links=True)
    items = getattr(parent, parent_link_field)
    assert len(items) == 0
