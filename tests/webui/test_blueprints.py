# type: ignore
"""Test the webui blueprints."""

import pytest

from tests.factories import *


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
async def test_character_view(
    debug, mocker, mock_session, test_client, character_factory, user_factory
) -> None:
    """Test the character blueprint."""
    user = user_factory.build()
    await user.insert()
    character = character_factory.build()
    await character.insert()
    mocker.patch(
        "valentina.webui.blueprints.character_view.route.is_storyteller", return_value=False
    )

    async with test_client.session_transaction() as session:
        session.update(mock_session(characters=[character], user_name=user.name, user_id=user.id))

    response = await test_client.get(f"/character/{character.id}", follow_redirects=True)

    assert response.status_code == 200

    for tab in ("sheet", "inventory", "profile", "statistics"):
        response = await test_client.get(
            f"/character/{character.id}?tab={tab}",
            headers={"HX-Request": "true"},
            follow_redirects=True,
        )
        # debug("headers", response.headers)
        assert response.status_code == 200


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


@pytest.mark.drop_db
async def test_gameplay_view(
    debug, mock_session, test_client, campaign_factory, character_factory
) -> None:
    """Test the gameplay blueprint."""
    campaign = campaign_factory.build()
    character = character_factory.build()
    await campaign.insert()
    await character.insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(campaigns=[campaign], characters=[character]))

    response = await test_client.get("/gameplay", follow_redirects=True)

    assert response.status_code == 200
