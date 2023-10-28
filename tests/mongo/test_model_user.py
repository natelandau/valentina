# type: ignore
"""Test the User model."""

import pytest
from rich import print

from valentina.utils import errors


async def test_campaign_experience(create_user, create_campaign) -> None:
    """Test the add_experience method."""
    # GIVEN a user and a campaign
    user = await create_user(new=True)
    campaign = await create_campaign()
    string_id = str(campaign.id)

    # WHEN add_experience is called with a campaign and an amount
    await user.add_campaign_xp(campaign, 10)

    # THEN check that the user has the correct amount of experience
    assert len(user.campaign_experience) == 1
    assert user.campaign_experience[string_id].xp_current == 10
    assert user.campaign_experience[string_id].xp_total == 10
    assert user.fetch_campaign_xp(campaign) == (10, 10, 0)

    # WHEN adding a cool point
    await user.add_campaign_cool_points(campaign, 2)

    # THEN check that the user has the correct amount of cool points
    assert len(user.campaign_experience) == 1
    assert user.campaign_experience[string_id].cool_points == 2

    # WHEN more experience is added
    await user.add_campaign_xp(campaign, 20)

    # THEN check that the user has the correct amount of experience
    assert len(user.campaign_experience) == 1
    assert user.campaign_experience[string_id].xp_current == 30
    assert user.campaign_experience[string_id].xp_total == 30
    assert user.fetch_campaign_xp(campaign) == (30, 30, 2)

    # WHEN experience is spent
    await user.spend_campaign_xp(campaign, 10)

    # THEN check that the user has the correct amount of experience
    assert len(user.campaign_experience) == 1
    assert user.campaign_experience[string_id].xp_current == 20
    assert user.campaign_experience[string_id].xp_total == 30
    assert user.fetch_campaign_xp(campaign) == (20, 30, 2)

    # WHEN checking lifetime experience and cool points
    # THEN check that the user has the correct amounts
    assert user.lifetime_experience == 30
    assert user.lifetime_cool_points == 2

    # WHEN trying to spend more experience than a user has
    # THEN check a ValueError is raised
    with pytest.raises(
        errors.NotEnoughExperienceError, match=r"Can not spend \d+ xp with only \d+ available"
    ):
        await user.spend_campaign_xp(campaign, 100)


async def test_user_characters(create_user, create_character, mock_guild1):
    """Test methods related to working with characters associated with the user."""
    # GIVEN a users and two characters
    user = await create_user(guilds=[mock_guild1.id, 223344])
    character1 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )

    character2 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )

    character3 = await create_character(guild=222222, user=user, type_player=True, add_to_user=True)

    # WHEN fetching the characters for a guild
    result = user.all_characters(mock_guild1)

    # THEN check that the correct characters are returned
    assert len(result) == 2
    assert result[0] == character1
    assert result[1] == character2

    # WHEN fetching an active character for a guild with no active character
    # THEN check that a NoActiveCharacterError is raised
    with pytest.raises(errors.NoActiveCharacterError):
        user.active_character(mock_guild1)

    # WHEN adding an active character
    await user.set_active_character(character1)

    # THEN check that the active character is set
    assert user.active_character(mock_guild1).id == character1.id

    # WHEN adding a different active character
    await user.set_active_character(character2)

    # THEN make sure the active character is switched
    assert user.active_character(mock_guild1).id == character2.id

    # WHEN removing a character
    await user.remove_character(character2)

    # THEN check that the character is removed
    assert len(user.characters) == 2
    assert character1 in user.characters
    assert character3 in user.characters
    assert character2 not in user.characters
    with pytest.raises(errors.NoActiveCharacterError):
        user.active_character(mock_guild1)
