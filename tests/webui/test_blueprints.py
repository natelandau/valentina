# type: ignore
"""Test the webui blueprints."""

import json

import pytest
from quart import url_for

from tests.factories import *
from valentina.webui.blueprints.character_view.route import CharacterViewTab
from valentina.webui.blueprints.diceroll_modal.route import RollType


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
async def test_routes(
    mocker, debug, test_client, mock_session, path, data, method, status_code
) -> None:
    """Test routes return 200."""
    mocker.patch("valentina.webui.utils.helpers.is_storyteller", return_value=False)

    if method == "GET":
        response = await test_client.get(path, data=data, follow_redirects=True)
    elif method == "POST":
        response = await test_client.post(path, data=data, follow_redirects=True)

    # debug("data", response.response.data)
    # debug("headers", response.headers)
    # debug("status_code", response.status_code)
    # debug("session", session)
    assert response.status_code == status_code


@pytest.mark.drop_db
async def test_character_views(
    debug, mocker, mock_session, test_client, campaign_factory, character_factory, user_factory
) -> None:
    """Test the character blueprint."""
    user = user_factory.build()
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    character = character_factory.build(campaign=str(campaign.id))
    await character.insert()
    mocker.patch(
        "valentina.webui.blueprints.character_view.route.is_storyteller", return_value=False
    )

    async with test_client.session_transaction() as session:
        session.update(mock_session(characters=[character], user_name=user.name, user_id=user.id))

    # Check the main character view
    response = await test_client.get(f"/character/{character.id}", follow_redirects=True)

    assert response.status_code == 200

    # Skip checking the images tab b/c mocking the AWS S3 bucket is difficult
    for tab in [x.value for x in CharacterViewTab if x.name != "IMAGES"]:
        response = await test_client.get(
            f"/character/{character.id}?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # debug("headers", response.headers)
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
    mocker.patch(
        "valentina.webui.blueprints.character_view.route.is_storyteller", return_value=False
    )

    async with test_client.session_transaction() as session:
        session.update(
            mock_session(
                characters=[character], user_name=user.name, user_id=user.id, guild_id=guild.id
            )
        )

    # Check the main character view
    response = await test_client.get(f"/character/{character.id}", follow_redirects=True)

    response = await test_client.get(
        f"/character/{character.id}/{campaign.id}/diceroll",
        headers={"HX-Request": "true"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    for tab in [x.value for x in RollType]:
        response = await test_client.get(
            f"/character/{character.id}/{campaign.id}/diceroll?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    # Test the results page but not macros b/c they are difficult to mock
    for roll_type in [x.value for x in RollType if x.name != "MACROS"]:
        mock_form_data = {
            "roll_type": roll_type,
            "dice_size": "10",
            "pool": "3",
            "difficulty": "6",
            "desperation_dice": "0",
            "trait1": json.dumps(
                {"id": str(trait1.id), "value": trait1.value, "name": trait1.name}
            ),
            "trait2": json.dumps(
                {"id": str(trait2.id), "value": trait2.value, "name": trait2.name}
            ),
        }
        response = await test_client.post(
            f"/character/{character.id}/{campaign.id}/diceroll/results",
            form=mock_form_data,
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        # assert "1d10" in (await response.get_data(as_text=True))


@pytest.mark.drop_db
async def test_campaign_view(debug, mock_session, test_client, campaign_factory) -> None:
    """Test the campaign blueprint."""
    campaign = campaign_factory.build()
    await campaign.insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(campaigns=[campaign]))

    response = await test_client.get(f"/campaign/{campaign.id}", follow_redirects=True)

    assert response.status_code == 200

    for tab in ("overview", "books", "characters", "statistics"):
        response = await test_client.get(
            f"/campaign/{campaign.id}?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        assert response.status_code == 200
