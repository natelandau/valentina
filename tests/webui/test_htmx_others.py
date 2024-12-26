# type: ignore
"""Test assorted forms using HTMXPartials."""

import pytest

from tests.factories import *


@pytest.mark.drop_db
async def test_set_desperation_or_danger(debug, mocker, test_client, campaign_factory):
    """Test the set desperation or danger form."""
    # Given: Mock audit log to avoid external calls during test
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.others.post_to_audit_log", return_value=None
    )
    # And: Create campaign with initial desperation and danger values
    campaign = await campaign_factory.build(desperation=0, danger=0).insert()

    url = f"/partials/setdesperation/{campaign.id}"

    # When: Request desperation form
    response = await test_client.get(url, follow_redirects=True)
    # Then: Return form HTML successfully
    assert response.status_code == 200

    # When: Submit form with incremented desperation and danger values
    response = await test_client.post(
        url, form={"desperation": 1, "danger": 1, "submit": True}, follow_redirects=True
    )
    # Then: Accept form submission
    assert response.status_code == 200

    # And: Persist updated values to database
    await campaign.sync()
    assert campaign.desperation == 1
    assert campaign.danger == 1


@pytest.mark.drop_db
async def test_experience_table_load(debug, mock_session, test_client, guild_factory, user_factory):
    """Test experience table load."""
    # Given: Create a guild and user, and link them together
    guild = await guild_factory.build().insert()
    user = await user_factory.build().insert()
    user.guilds.append(guild.id)
    await user.save()

    # When: Set up an authenticated session for the user
    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    # Then: Verify experience table loads successfully for the user
    response = await test_client.get(f"/partials/addexperience/{user.id}")
    assert response.status_code == 200


@pytest.mark.drop_db
async def test_experience_table_crud_operations(
    debug, mocker, guild_factory, mock_session, test_client, campaign_factory, user_factory
):
    """Test experience table crud operations."""
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.others.post_to_audit_log", return_value=None
    )

    # Given: Create a guild, campaign and user with storyteller permissions
    # Guild and campaign are needed since XP is tracked per campaign
    guild = await guild_factory.build().insert()
    campaign = await campaign_factory.build(guild=guild.id).insert()
    user = await user_factory.build(campaign=str(campaign.id)).insert()

    # Link user to guild and grant storyteller permissions to allow XP granting
    user.guilds.append(guild.id)
    await user.save()
    guild.campaigns.append(campaign)
    guild.storytellers.append(user.id)
    await guild.save()

    # Set up session to authenticate as the storyteller user
    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    # When: Submit form to add both experience and cool points
    form_data = {
        "campaign": str(campaign.id),
        "experience": "100",
        "cool_points": "100",
        "submit": "true",
    }
    response = await test_client.post(
        f"/partials/addexperience/{user.id}", json=form_data, follow_redirects=True
    )

    # Then the request succeeds and experience is updated correctly
    assert response.status_code == 200

    # And: Experience is correctly calculated and stored
    # Cool points are worth 10 XP each, so total XP should be:
    # Direct XP (100) + Cool Point XP (100 * 10) = 1100
    updated_user = await User.get(user.id, fetch_links=True)
    campaign_xp = updated_user.fetch_campaign_xp(campaign)
    assert campaign_xp == (1100, 1100, 100)  # (current_xp, total_xp, cool_points)
