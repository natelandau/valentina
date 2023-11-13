# type: ignore
"""Test the experience cog."""

from unittest.mock import AsyncMock

import pytest
from tests.factories import *

from valentina.cogs.experience import Experience
from valentina.constants import TraitCategory
from valentina.models import CampaignExperience, CharacterTrait, User
from valentina.utils import errors


@pytest.mark.drop_db()
async def test_xp_add(async_mock_ctx1, mock_bot, user_factory, campaign_factory):
    """Test the xp_add command."""
    # GIVEN a mock context, a user, and a campaign
    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # MOCK call to fetch_active_campaign
    async_mock_ctx1.fetch_active_campaign = AsyncMock(return_value=campaign)

    # WHEN the xp_add command is called
    await Experience(bot=mock_bot).xp_add(
        async_mock_ctx1,
        amount=10,
        user=None,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (10, 10, 0)


@pytest.mark.drop_db()
async def test_cp_add(async_mock_ctx1, mock_bot, user_factory, campaign_factory):
    """Test the cp_add command."""
    # GIVEN a mock context, a user, and a campaign
    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        active_characters={},
        characters=[],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # MOCK call to fetch_active_campaign
    async_mock_ctx1.fetch_active_campaign = AsyncMock(return_value=campaign)

    # WHEN the xp_add command is called
    await Experience(bot=mock_bot).cp_add(
        async_mock_ctx1,
        amount=1,
        user=None,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (10, 10, 1)


@pytest.mark.drop_db()
async def test_xp_spend(
    async_mock_ctx1, mock_bot, user_factory, campaign_factory, trait_factory, character_factory
):
    """Test the cp_add command."""
    # GIVEN a mock context, a user, a trait, and a campaign
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=5
    )
    await trait.insert()

    character = character_factory.build(traits=[trait])

    campaign = campaign_factory.build()
    await campaign.insert()

    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        active_characters={},
        characters=[],
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=30, xp_total=30, cool_points=1)
        },
        macros=[],
    )
    await user.insert()

    # MOCK call to fetch_active_campaign
    async_mock_ctx1.fetch_active_campaign = AsyncMock(return_value=campaign)

    # WHEN the xp_add command is called
    await Experience(bot=mock_bot).xp_spend(
        async_mock_ctx1,
        character=character,
        trait=trait,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (15, 30, 1)
    db_trait = await CharacterTrait.get(trait.id)
    assert db_trait.value == 3


@pytest.mark.drop_db()
async def test_xp_spend_not_enough_xp(
    async_mock_ctx1, mock_bot, user_factory, campaign_factory, trait_factory, character_factory
):
    """Test the cp_add command."""
    # GIVEN a mock context, a user, a trait, and a campaign
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=5
    )
    await trait.insert()

    character = character_factory.build(traits=[trait])

    campaign = campaign_factory.build()
    await campaign.insert()

    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        active_characters={},
        characters=[],
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=10, xp_total=30, cool_points=1)
        },
        macros=[],
    )
    await user.insert()

    # MOCK call to fetch_active_campaign
    async_mock_ctx1.fetch_active_campaign = AsyncMock(return_value=campaign)

    # WHEN the xp_add command is called
    with pytest.raises(errors.NotEnoughExperienceError):
        await Experience(bot=mock_bot).xp_spend(
            async_mock_ctx1,
            character=character,
            trait=trait,
            hidden=False,
        )
