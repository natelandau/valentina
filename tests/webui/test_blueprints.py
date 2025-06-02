# type: ignore
"""Test the webui blueprints."""

import json

import pytest

from tests.factories import *
from valentina.models import DictionaryTerm
from valentina.webui.blueprints.diceroll_modal.route import RollType
from valentina.webui.constants import (
    CampaignEditableInfo,
    CampaignViewTab,
    CharacterEditableInfo,
    CharacterViewTab,
)


@pytest.mark.parametrize(
    (
        "method",
        "path",
        "data",
        "status_code",
    ),
    [
        ("GET", "/", {}, 200),
        ("GET", "/user-guide", {}, 200),
        ("GET", "/robots.txt", {}, 200),
        ("GET", "/does_not_exist", {}, 404),
    ],
)
@pytest.mark.drop_db
async def test_static_routes(mocker, debug, test_client, path, data, method, status_code) -> None:
    """Test routes return 200."""
    # Given: The user is not a storyteller
    mocker.patch("valentina.webui.utils.helpers.is_storyteller", return_value=False)

    # When: The user makes a request to the route
    if method == "GET":
        response = await test_client.get(path, data=data, follow_redirects=True)
    elif method == "POST":
        response = await test_client.post(path, data=data, follow_redirects=True)

    # Then: The response has the expected status code
    assert response.status_code == status_code


@pytest.mark.drop_db
async def test_admin_blueprint(debug, mocker, mock_session, test_client, guild_factory):
    """Test the admin blueprint."""
    # Given: A test environment with mocked dependencies
    mocker.patch("valentina.webui.blueprints.admin.route.is_storyteller", return_value=True)
    mocker.patch("valentina.webui.blueprints.admin.route.post_to_audit_log", return_value=None)

    # And: A guild exists in the database
    guild = guild_factory.build()
    await guild.insert()

    # And: The user has an active session with the guild
    async with test_client.session_transaction() as session:
        session.update(mock_session(guild_id=guild.id))

    # When: The user visits the admin page
    response = await test_client.get("/admin/", follow_redirects=True)

    # Then: The page loads successfully
    assert response.status_code == 200

    # When: The user updates each permission setting with valid values
    for arg in ["grant_xp", "manage_traits", "manage_campaigns", "kill_character"]:
        response = await test_client.post(f"/admin?{arg}=1", follow_redirects=True)
        # Then: The update succeeds
        assert response.status_code == 200

        # When: The user attempts to update with invalid values
        response = await test_client.post(f"/admin?{arg}=100", follow_redirects=True)
        # Then: The update fails with bad request
        assert response.status_code == 400


@pytest.mark.drop_db
async def test_character_views(
    debug,
    mocker,
    mock_session,
    test_client,
    campaign_factory,
    character_factory,
    user_factory,
) -> None:
    """Test the character blueprint."""
    # Given: The user is not a storyteller
    mocker.patch(
        "valentina.webui.blueprints.character_view.route.is_storyteller",
        return_value=False,
    )

    # And: A user exists in the database
    user = user_factory.build()
    await user.insert()

    # And: A campaign exists in the database
    campaign = campaign_factory.build()
    await campaign.insert()

    # And: A character exists in the database linked to the user and campaign
    character = character_factory.build(campaign=str(campaign.id), user_owner=user.id)
    await character.insert()

    # And: The user has an active session with the character
    async with test_client.session_transaction() as session:
        session.update(mock_session(characters=[character], user_name=user.name, user_id=user.id))

    # When: The user visits the main character view
    response = await test_client.get(f"/character/{character.id}", follow_redirects=True)

    # Then: The page loads successfully
    assert response.status_code == 200

    # When: The user visits each character tab except images
    for tab in [x.value for x in CharacterViewTab if x.name != "IMAGES"]:
        response = await test_client.get(
            f"/character/{character.id}?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        # Then: Each tab loads successfully
        assert response.status_code == 200


@pytest.mark.drop_db
async def test_character_edit_routes(
    debug,
    mocker,
    mock_session,
    test_client,
    character_factory,
) -> None:
    """Test the character edit blueprint."""
    # Given: A character exists in the database
    character = character_factory.build()
    await character.insert()

    # And: The user has an active session
    async with test_client.session_transaction() as session:
        session.update(mock_session())

    # When: The user visits each editable route for the character
    for route in [x.value.name for x in CharacterEditableInfo]:
        response = await test_client.get(
            f"/character/{character.id}/edit/{route}",
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        # Then: The response is successful
        assert response.status_code == 200


@pytest.mark.drop_db
async def test_diceroll_modal(
    debug,
    mocker,
    mock_session,
    test_client,
    campaign_factory,
    guild_factory,
    character_factory,
    user_factory,
    trait_factory,
) -> None:
    """Test the character blueprint."""
    # Given: A set of traits, user, campaign, guild and character exist in the database
    trait1 = trait_factory.build()
    await trait1.insert()
    trait2 = trait_factory.build()
    await trait2.insert()

    user = user_factory.build()
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    guild = guild_factory.build()
    await guild.insert()

    character = character_factory.build(campaign=str(campaign.id), traits=[trait1, trait2])
    await character.insert()

    # And: The user is not a storyteller
    mocker.patch(
        "valentina.webui.blueprints.character_view.route.is_storyteller",
        return_value=False,
    )

    # And: The user has an active session
    async with test_client.session_transaction() as session:
        session.update(
            mock_session(
                characters=[character],
                user_name=user.name,
                user_id=user.id,
                guild_id=guild.id,
            ),
        )

    # When: The user visits the main character view
    response = await test_client.get(f"/character/{character.id}", follow_redirects=True)

    # And: The user opens the diceroll modal
    response = await test_client.get(
        f"/character/{character.id}/{campaign.id}/diceroll",
        headers={"HX-Request": "true"},
        follow_redirects=True,
    )
    # Then: The modal loads successfully
    assert response.status_code == 200

    # When: The user visits each roll type tab
    for tab in [x.value for x in RollType]:
        response = await test_client.get(
            f"/character/{character.id}/{campaign.id}/diceroll?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # Then: Each tab loads successfully
        assert response.status_code == 200

    # When: The user submits dice rolls for each roll type (except macros)
    for roll_type in [x.value for x in RollType if x.name != "MACROS"]:
        mock_form_data = {
            "roll_type": roll_type,
            "dice_size": "10",
            "pool": "3",
            "difficulty": "6",
            "desperation_dice": "0",
            "trait1": json.dumps(
                {"id": str(trait1.id), "value": trait1.value, "name": trait1.name},
            ),
            "trait2": json.dumps(
                {"id": str(trait2.id), "value": trait2.value, "name": trait2.name},
            ),
        }
        response = await test_client.post(
            f"/character/{character.id}/{campaign.id}/diceroll/results",
            form=mock_form_data,
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # Then: The roll results load successfully
        assert response.status_code == 200
        # assert "1d10" in (await response.get_data(as_text=True))


@pytest.mark.drop_db
async def test_campaign_view(
    debug,
    mock_session,
    guild_factory,
    test_client,
    campaign_factory,
) -> None:
    """Test the campaign blueprint."""
    # Given: A guild and campaign exist in the database
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # And: The user has an active session with the campaign and guild
    async with test_client.session_transaction() as session:
        session.update(mock_session(campaigns=[campaign], guild_id=guild.id))

    # When: The user visits the campaign view page
    response = await test_client.get(f"/campaign/{campaign.id}", follow_redirects=True)

    # Then: The page loads successfully
    assert response.status_code == 200

    # When: The user visits each campaign tab
    for tab in [x.value for x in CampaignViewTab]:
        response = await test_client.get(
            f"/campaign/{campaign.id}?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        # Then: Each tab loads successfully
        assert response.status_code == 200


@pytest.mark.drop_db
async def test_campaign_edit_routes(
    debug,
    mock_session,
    guild_factory,
    test_client,
    campaign_factory,
) -> None:
    """Test the character edit blueprint."""
    # Given: A guild and campaign exist in the database
    guild = guild_factory.build()
    await guild.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # And: The user has an active session with the campaign and guild
    async with test_client.session_transaction() as session:
        session.update(mock_session(campaigns=[campaign], guild_id=guild.id))

    # When: The user visits each campaign edit route
    for route in [x.value.name for x in CampaignEditableInfo]:
        response = await test_client.get(
            f"/campaign/{campaign.id}/edit/{route}",
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        # Then: The page loads successfully
        assert response.status_code == 200


@pytest.mark.drop_db
async def test_dictionary_blueprint(debug, mock_session, test_client):
    """Test the dictionary blueprint."""
    # Given: A dictionary term exists in the database
    term = DictionaryTerm(
        term="aaaaa",
        synonyms=["bbbbb"],
        definition="abcdefg",
        guild_id=1,
    )
    await term.insert()

    # And: The user is in a guild session
    async with test_client.session_transaction() as session:
        session.update(mock_session(guild_id=1))

    # When: The user requests a specific dictionary term
    response = await test_client.get("/dictionary/term/aaaaa", follow_redirects=True)
    # Then: The term page loads successfully
    assert response.status_code == 200

    # When: The user requests the main dictionary page
    response = await test_client.get("/dictionary", follow_redirects=True)
    # Then: The dictionary page loads successfully
    assert response.status_code == 200
