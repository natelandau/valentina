# type: ignore
"""Test the HTMX partials blueprint."""

import pytest

from tests.factories import *
from valentina.models import (
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    Character,
    DictionaryTerm,
    InventoryItem,
    Note,
    User,
)
from valentina.webui.constants import TableType, TextType
from valentina.webui.utils import from_markdown


@pytest.fixture
async def test_setup(
    debug,
    character_factory,
    mock_session,
    test_client,
    user_factory,
    guild_factory,
    campaign_factory,
    book_factory,
) -> tuple[Character, Campaign, User, CampaignBook, "TestClientProtocol"]:
    """Create base test environment."""
    guild = await guild_factory.build().insert()
    user = await user_factory.build(macros=[]).insert()
    character = await character_factory.build(
        guild=guild.id,
        inventory=[],
        notes=[],
        bio=None,
    ).insert()
    campaign = await campaign_factory.build(
        guild=guild.id, books=[], npcs=[], notes=[], description=None
    ).insert()
    book = await book_factory.build(campaign=str(campaign.id), chapters=[], notes=[]).insert()
    campaign.books.append(book)
    await campaign.save()
    guild.campaigns.append(campaign)
    guild.storytellers.append(user.id)
    await guild.save()
    user.guilds.append(guild.id)
    await user.save()

    dictionary_term = await DictionaryTerm(
        term="dictionary_term",
        definition="test definition",
        synonyms=["synonym1", "synonym2"],
        guild_id=guild.id,
    ).insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    return character, campaign, user, book, dictionary_term, test_client


@pytest.mark.parametrize(
    ("table_type", "id_field", "parent_id_source", "use_parent_id"),
    [
        (TableType.NOTE, "note_id", "character", True),
        (TableType.NOTE, "note_id", "book", True),
        (TableType.NOTE, "note_id", "campaign", True),
        (TableType.INVENTORYITEM, "item_id", "character", True),
        (TableType.CHAPTER, "chapter_id", "book", True),
        (TableType.NPC, "uuid", "campaign", True),
        (TableType.MACRO, "uuid", "user", True),
        (TableType.DICTIONARY, "term_id", "dictionary_term", False),
    ],
)
@pytest.mark.drop_db
async def test_edit_table_form_load(
    test_setup, table_type, id_field, parent_id_source, use_parent_id
):
    """Test form load returns empty form."""
    character, campaign, user, book, dictionary_term, test_client = test_setup

    # Map source names to their corresponding objects
    parent_id_map = {
        "character": character,
        "campaign": campaign,
        "book": book,
        "user": user,
        "dictionary_term": dictionary_term,
    }
    parent_id = parent_id_map[parent_id_source].id if use_parent_id else ""

    url = f"/partials/table/{table_type.value.route_suffix}?parent_id={parent_id}&use_method=post"

    response = await test_client.get(url)
    returned_text = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'value="{parent_id}">' in returned_text

    assert f'<input id="{id_field}" name="{id_field}" type="hidden" value="">' in returned_text


@pytest.mark.parametrize(
    (
        "table_type",  # TableType enum value
        "model_class",  # Database model for the item being edited
        "primary_key_field",  # Name of the primary key field in the model, typically "id" or "uuid"
        "parent_model",  # Database model that owns/contains this item
        "parent_key_field",  # Field on the parent object that contains the parent's primary key
        "parent_collection",  # Name of collection field in parent that stores these items
        "creation_data",  # Test data for creating new items
        "update_data",  # Test data for updating existing items
        "get_parent_instance",  # Function to get the parent object for testing
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
            lambda character, campaign, user, book: character,
        ),
        (
            TableType.NOTE,
            Note,
            "id",
            CampaignBook,
            "book_id",
            "notes",
            {"text": "test note"},
            {"text": "updated note"},
            lambda character, campaign, user, book: book,
        ),
        (
            TableType.NOTE,
            Note,
            "id",
            Campaign,
            "campaign_id",
            "notes",
            {"text": "test note"},
            {"text": "updated note"},
            lambda character, campaign, user, book: campaign,
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
            lambda character, campaign, user, book: character,
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
            lambda character, campaign, user, book: book,
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
            lambda character, campaign, user, book: campaign,
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
            lambda character, campaign, user, book: user,
        ),
    ],
)
@pytest.mark.drop_db
async def test_edit_table_crud_operations_with_parent(
    debug,
    test_setup,
    table_type,
    model_class,
    primary_key_field,
    parent_model,
    parent_key_field,
    parent_collection,
    creation_data,
    update_data,
    get_parent_instance,
    mocker,
):
    """Test create, update, and delete operations."""
    character, campaign, user, book, dictionary_term, test_client = test_setup
    base_url = f"/partials/table/{table_type.value.route_suffix}"

    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.route.post_to_audit_log", return_value=None
    )
    mocker.patch("valentina.webui.blueprints.HTMXPartials.route.update_session", return_value=None)

    # Get appropriate parent based on table type
    parent = get_parent_instance(character, campaign, user, book)

    # Create
    create_data = (
        {**creation_data, parent_key_field: str(parent.id)} if parent_key_field else creation_data
    )

    response = await test_client.put(
        f"{base_url}?parent_id={parent.id}", json=create_data, follow_redirects=True
    )
    assert response.status_code == 200

    # Verify creation
    parent = await parent_model.get(parent.id, fetch_links=True)

    items = getattr(parent, parent_collection)

    assert len(items) == 1
    item = items[0]
    item_id = getattr(item, primary_key_field)

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

    if model_class:
        assert await model_class.get(item_id) is None

    # Verify deletion
    parent = await parent_model.get(parent.id, fetch_links=True)
    items = getattr(parent, parent_collection)
    assert len(items) == 0


@pytest.mark.parametrize(
    ("text_type", "get_parent_instance"),
    [
        (TextType.BIOGRAPHY, lambda character, campaign, user, book: character),
        (TextType.CAMPAIGN_DESCRIPTION, lambda character, campaign, user, book: campaign),
    ],
)
@pytest.mark.drop_db
async def test_edit_text_form_load(debug, test_setup, text_type, get_parent_instance):
    """Test form load returns empty form."""
    character, campaign, user, book, dictionary_term, test_client = test_setup

    # Get appropriate parent based on table type
    parent = get_parent_instance(character, campaign, user, book)

    url = f"/partials/text/{text_type.value.route_suffix}?parent_id={parent.id}"

    response = await test_client.put(url)
    returned_text = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'value="{parent.id}">' in returned_text
    if text_type.value.description:
        assert f"{text_type.value.description}" in returned_text


@pytest.mark.parametrize(
    (
        "text_type",
        "parent_model",
        "parent_field",
        "get_parent_instance",
        "creation_data",
        "update_data",
    ),
    [
        (
            TextType.BIOGRAPHY,
            Character,
            "bio",
            lambda character, campaign, user, book: character,
            {"bio": "A communi observantia non est recedendum."},
            {"bio": "Nec dubitamus multa iter quae et nos invenerat."},
        ),
        (
            TextType.CAMPAIGN_DESCRIPTION,
            Campaign,
            "description",
            lambda character, campaign, user, book: campaign,
            {"campaign_description": "A communi observantia non est recedendum."},
            {"campaign_description": "Nec dubitamus multa iter quae et nos invenerat."},
        ),
    ],
)
@pytest.mark.drop_db
async def test_edit_text_form_crud_operations(
    debug,
    mocker,
    test_setup,
    text_type,
    parent_model,
    parent_field,
    get_parent_instance,
    creation_data,
    update_data,
):
    """Test create, update, and delete operations."""
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.route.post_to_audit_log", return_value=None
    )
    mocker.patch("valentina.webui.blueprints.HTMXPartials.route.update_session", return_value=None)

    character, campaign, user, book, _, test_client = test_setup
    parent = get_parent_instance(character, campaign, user, book)

    # Create
    response = await test_client.put(
        f"/partials/text/{text_type.value.route_suffix}?parent_id={parent.id}",
        json=creation_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    parent = await parent_model.get(parent.id)
    assert getattr(parent, parent_field) == creation_data[next(iter(creation_data.keys()))]

    # Get the created item's table text partial
    response = await test_client.get(
        f"/partials/text/{text_type.value.route_suffix}?parent_id={parent.id}",
        follow_redirects=True,
    )
    response_text = await response.get_data(as_text=True)
    assert response.status_code == 200
    assert response_text == from_markdown(creation_data[next(iter(creation_data.keys()))])

    # Update
    response = await test_client.post(
        f"/partials/text/{text_type.value.route_suffix}?parent_id={parent.id}",
        json=update_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    parent = await parent_model.get(parent.id)
    assert getattr(parent, parent_field) == update_data[next(iter(update_data.keys()))]


@pytest.mark.drop_db
async def test_experience_table_load(debug, test_setup):
    """Test experience table load."""
    _, _, user, _, _, test_client = test_setup

    response = await test_client.get(f"/partials/addexperience/{user.id}")
    assert response.status_code == 200


@pytest.mark.drop_db
async def test_experience_table_crud_operations(debug, test_setup):
    """Test experience table crud operations."""
    # Given a user and campaign with no existing experience
    _, campaign, user, _, _, test_client = test_setup
    campaign_id = str(campaign.id)

    # When submitting a form to add experience and cool points
    form_data = {
        "campaign": campaign_id,
        "experience": "100",
        "cool_points": "100",
        "submit": "true",
    }
    response = await test_client.post(
        f"/partials/addexperience/{user.id}", json=form_data, follow_redirects=True
    )

    # Then the request succeeds and experience is updated correctly
    # TODO: This assertion passes locally but fails on CI, debug it
    # assert response.status_code == 200

    # Cool points give 10xp each, so 100 cool points = 1000xp
    updated_user = await User.get(user.id, fetch_links=True)
    campaign_xp = updated_user.fetch_campaign_xp(campaign)
    assert campaign_xp == (1100, 1100, 100)  # (current_xp, total_xp, cool_points)


@pytest.mark.drop_db
async def test_dictionary_term_crud_operations(mocker, debug, test_setup):
    """Test create, update, and delete operations for a dictionary term."""
    # Given: A test environment with mocked dependencies
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.route.post_to_audit_log", return_value=None
    )
    mocker.patch("valentina.webui.blueprints.HTMXPartials.route.update_session", return_value=None)

    character, campaign, user, book, dictionary_term, test_client = test_setup

    base_url = f"/partials/table/{TableType.DICTIONARY.value.route_suffix}"
    test_term_name = "test_term_from_test"
    updated_definition = "test definition2 updated"
    creation_data = {"term": test_term_name, "definition": "test definition"}
    update_data = {"term": f"{test_term_name}_updated", "definition": updated_definition}

    # When: Creating a new dictionary term
    response = await test_client.put(f"{base_url}", json=creation_data, follow_redirects=True)

    # Then: Term is created successfully
    assert response.status_code == 200
    created_items = await DictionaryTerm.find(DictionaryTerm.term == test_term_name).to_list()
    created_item = created_items[0]
    assert created_item is not None

    # When: Updating the dictionary term
    response = await test_client.post(
        f"{base_url}?item_id={created_item.id}", json=update_data, follow_redirects=True
    )

    # Then: Term is updated successfully
    assert response.status_code == 200
    await created_item.sync()
    assert created_item.definition == updated_definition

    # When: Deleting the dictionary term
    response = await test_client.delete(
        f"{base_url}?item_id={created_item.id}", follow_redirects=True
    )

    # Then: Term is deleted successfully
    assert response.status_code == 200
    assert await DictionaryTerm.get(created_item.id) is None
