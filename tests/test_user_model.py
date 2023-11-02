# type: ignore
"""Test the User model."""

import pytest
from rich import print

from valentina.utils import errors

from .factories import *


async def test_add_experience(user_factory, campaign_factory) -> None:
    """Test the add_experience method."""
    # GIVEN a user and a campaign
    user = user_factory.build(
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    campaign = campaign_factory.build()
    await campaign.insert()
    await user.insert()

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


async def test_add_campaign_cool_points(user_factory, campaign_factory) -> None:
    """Test the add_campaign_cool_points method."""
    # GIVEN a user and a campaign
    user = user_factory.build(
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    campaign = campaign_factory.build()
    await campaign.insert()
    await user.insert()
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


async def test_spend_spend_campaign_xp(user_factory, campaign_factory) -> None:
    """Test the spend_campaign_xp method."""
    # GIVEN a new user and a campaign and 20 experience
    user = user_factory.build(
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    campaign = campaign_factory.build()
    await campaign.insert()
    await user.insert()
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


@pytest.mark.no_db()
async def test_all_user_characters(mock_guild1, user_factory, character_factory) -> None:
    """Test methods related to working with characters associated with the user."""
    # GIVEN a users and three characters
    user = user_factory.build(guilds=[mock_guild1.id, 223344])
    character1 = character_factory.build(guild=mock_guild1.id, user_owner=user.id, type_player=True)
    character2 = character_factory.build(guild=mock_guild1.id, user_owner=user.id, type_player=True)
    character3 = character_factory.build(guild=223344, user_owner=user.id, type_player=True)

    user.characters = [character1, character2, character3]

    # WHEN fetching the characters for a guild
    result = user.all_characters(mock_guild1)

    # THEN check that the correct characters are returned
    assert len(result) == 2
    assert result[0] == character1
    assert result[1] == character2


async def test_set_active_character(mock_guild1, user_factory, character_factory):
    """Test the set_active_character method."""
    # Given a user and two characters
    user = user_factory.build(
        guilds=[mock_guild1.id, 223344],
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    character1 = character_factory.build(
        guild=mock_guild1.id, user_owner=user.id, type_player=True, traits=[]
    )
    character2 = character_factory.build(
        guild=mock_guild1.id, user_owner=user.id, type_player=True, traits=[]
    )
    await character1.insert()
    await character2.insert()
    user.characters = [character1]
    await user.insert()

    # WHEN adding an active character
    await user.set_active_character(character1)

    # THEN check that the active character is set
    active_char = await user.active_character(mock_guild1)
    assert active_char.id == character1.id
    assert active_char.id in [x.id for x in user.characters]

    # WHEN adding a different active character
    await user.set_active_character(character2)

    # THEN make sure the active character is switched
    new_active_char = await user.active_character(mock_guild1)
    assert new_active_char.id == character2.id
    assert new_active_char.id in [x.id for x in user.characters]
    assert active_char.id in [x.id for x in user.characters]


@pytest.mark.no_db()
async def test_active_character(user_factory, character_factory, mock_guild1):
    """Test failure methods related to working with the active character."""
    # Given a user and two characters
    user = user_factory.build(
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    character1 = character_factory.build(
        guild=2222, user_owner=user.id, type_player=True, traits=[]
    )
    user.characters = [character1]
    user.active_characters = {2222: character1}

    # WHEN fetching an active character for a guild with no active character
    # THEN check that a NoActiveCharacterError is raised
    with pytest.raises(errors.NoActiveCharacterError):
        await user.active_character(mock_guild1)

    # WHEN fetching an active character for a guild with no active character and not raising an error
    # THEN check that a None is returned
    assert await user.active_character(mock_guild1, raise_error=False) is None


async def test_remove_character(user_factory, character_factory, mock_guild1):
    """Test the remove_character method."""
    # GIVEN a user and two characters, one of which is active
    # Given a user and two characters
    user = user_factory.build(
        guilds=[mock_guild1.id, 223344],
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    character1 = character_factory.build(
        guild=mock_guild1.id, user_owner=user.id, type_player=True, traits=[]
    )
    character2 = character_factory.build(
        guild=mock_guild1.id, user_owner=user.id, type_player=True, traits=[]
    )
    await character1.insert()
    await character2.insert()
    user.characters = [character1, character2]
    await user.insert()

    await user.set_active_character(character2)
    result = await user.active_character(mock_guild1)
    assert result.id == character2.id

    # WHEN removing a character
    await user.remove_character(character2)

    # THEN check that the character is removed
    assert len(user.characters) == 1
    assert character1.id in [x.id for x in user.characters]
    assert character2.id not in [x.id for x in user.characters]
    with pytest.raises(errors.NoActiveCharacterError):
        await user.active_character(mock_guild1)
