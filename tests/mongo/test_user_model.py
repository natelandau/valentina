# type: ignore
"""Test the User model."""

import pytest
from rich import print

from valentina.utils import errors


async def test_add_experience(create_user, create_campaign) -> None:
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

    # WHEN more experience is added
    await user.add_campaign_xp(campaign, 20)

    # THEN check that the user has the correct amount of experience
    assert len(user.campaign_experience) == 1
    assert user.campaign_experience[string_id].xp_current == 30
    assert user.campaign_experience[string_id].xp_total == 30
    assert user.fetch_campaign_xp(campaign) == (30, 30, 0)


async def test_add_campaign_cool_points(create_user, create_campaign) -> None:
    """Test the add_campaign_cool_points method."""
    # GIVEN a user and a campaign
    user = await create_user(new=True)
    campaign = await create_campaign()
    string_id = str(campaign.id)

    # WHEN add_campaign_cool_points is called with a campaign and an amount
    await user.add_campaign_cool_points(campaign, 2)

    # THEN check that the user has the correct amount of cool points and experience
    assert len(user.campaign_experience) == 1
    assert user.lifetime_cool_points == 2
    assert user.lifetime_experience == 20
    assert user.campaign_experience[string_id].cool_points == 2
    assert user.campaign_experience[string_id].xp_current == 20
    assert user.campaign_experience[string_id].xp_total == 20
    assert user.fetch_campaign_xp(campaign) == (20, 20, 2)


async def test_spend_spend_campaign_xp(create_user, create_campaign) -> None:
    """Test the spend_campaign_xp method."""
    # GIVEN a new user and a campaign and 20 experience
    user = await create_user(new=True)
    campaign = await create_campaign()
    string_id = str(campaign.id)
    await user.add_campaign_xp(campaign, 20)

    # WHEN experience is spent
    await user.spend_campaign_xp(campaign, 1)

    # THEN check that the user has the correct amount of experience
    assert user.campaign_experience[string_id].xp_current == 19
    assert user.campaign_experience[string_id].xp_total == 20
    assert user.fetch_campaign_xp(campaign) == (19, 20, 0)
    assert user.lifetime_experience == 20
    assert user.lifetime_cool_points == 0

    # WHEN trying to spend more experience than a user has
    # THEN check a ValueError is raised
    with pytest.raises(
        errors.NotEnoughExperienceError, match=r"Can not spend \d+ xp with only \d+ available"
    ):
        await user.spend_campaign_xp(campaign, 100)


async def test_all_user_characters(create_user, create_character, mock_guild1):
    """Test methods related to working with characters associated with the user."""
    # GIVEN a users and three characters
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


async def test_set_active_character(create_user, create_character, mock_guild1):
    """Test the set_active_character method."""
    # Given a user and two characters
    user = await create_user(guilds=[mock_guild1.id, 223344])
    character1 = await create_character(guild=mock_guild1.id, user=user, type_player=True)
    character2 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )

    # WHEN adding an active character
    await user.set_active_character(character1)

    # THEN check that the active character is set
    active_char = await user.active_character(mock_guild1)
    assert active_char == character1
    assert active_char in user.characters

    # WHEN adding a different active character
    await user.set_active_character(character2)

    # THEN make sure the active character is switched
    new_active_char = await user.active_character(mock_guild1)
    assert new_active_char == character2
    assert new_active_char in user.characters
    assert active_char in user.characters


async def test_active_character(create_user, create_character, mock_guild1):
    """Test methods related to working with the active character."""
    # Given a user and two characters
    user = await create_user(guilds=[mock_guild1.id, 223344])
    character1 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )
    character2 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )

    # WHEN fetching an active character for a guild with no active character
    # THEN check that a NoActiveCharacterError is raised
    with pytest.raises(errors.NoActiveCharacterError):
        await user.active_character(mock_guild1)

    # WHEN fetching an active character for a guild with no active character and not raising an error
    # THEN check that a None is returned
    assert await user.active_character(mock_guild1, raise_error=False) is None

    # GIVEN an active character
    await user.set_active_character(character1)

    # WHEN fetching an active character for a guild
    result = await user.active_character(mock_guild1)

    # THEN check that the correct character is returned
    assert result == character1


async def test_remove_character(create_user, create_character, mock_guild1):
    """Test the remove_character method."""
    # GIVEN a user and two characters, one of which is active
    user = await create_user(guilds=[mock_guild1.id, 223344])
    character1 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )
    character2 = await create_character(
        guild=mock_guild1.id, user=user, type_player=True, add_to_user=True
    )
    await user.set_active_character(character2)
    assert await user.active_character(mock_guild1) == character2

    # WHEN removing a character
    await user.remove_character(character2)

    # THEN check that the character is removed
    assert len(user.characters) == 1
    assert character1 in user.characters
    assert character2 not in user.characters
    with pytest.raises(errors.NoActiveCharacterError):
        await user.active_character(mock_guild1)
