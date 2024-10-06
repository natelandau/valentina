# type: ignore
"""Test the experience cog.

When pycord updated to v2.5.0 these tests broke. To fix them, the ctx needs to be added twice to each call to a cog. This is because the ctx is now the first argument in the method signature. This is a breaking change in pycord 2.5.0. 😕
"""

import pytest
from rich.console import Console
from tests.factories import *

from valentina.cogs.experience import Experience
from valentina.constants import TraitCategory
from valentina.models import CampaignExperience, CharacterTrait, User
from valentina.utils import errors

c = Console()


@pytest.mark.drop_db
async def test_xp_add(async_mock_ctx1, mock_bot, user_factory, campaign_factory):
    """Test the xp_add command."""
    # GIVEN a mock context, a user, and a campaign
    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        characters=[],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # WHEN the xp_add command is called
    cog = Experience(bot=mock_bot)
    await cog.xp_add(
        async_mock_ctx1,
        async_mock_ctx1,
        amount=10,
        user=None,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (10, 10, 0)


@pytest.mark.drop_db
async def test_cp_add(async_mock_ctx1, mock_bot, user_factory, campaign_factory):
    """Test the cp_add command."""
    # GIVEN a mock context, a user, and a campaign
    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        characters=[],
        campaign_experience={},
        macros=[],
    )
    await user.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    # WHEN the xp_add command is called
    await Experience(bot=mock_bot).cp_add(
        async_mock_ctx1,
        async_mock_ctx1,
        amount=1,
        user=None,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (10, 10, 1)


# @pytest.mark.skip(reason="Broke with pycord 2.5.0")
@pytest.mark.drop_db
async def test_xp_spend(
    async_mock_ctx1, mock_bot, user_factory, campaign_factory, trait_factory, character_factory
):
    """Test the xp_spend command."""
    # GIVEN a mock context, a user, a trait, and a campaign
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=5
    )
    await trait.insert()

    character = character_factory.build(traits=[trait])
    await character.insert()

    campaign = campaign_factory.build()
    await campaign.insert()

    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        characters=[],
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=30, xp_total=30, cool_points=1)
        },
        macros=[],
    )
    await user.insert()

    # WHEN the xp_add command is called
    await Experience(bot=mock_bot).xp_spend(
        async_mock_ctx1,
        async_mock_ctx1,
        trait=trait,
        hidden=False,
    )

    # THEN check that the user has the correct amount of experience
    db_user = await User.get(async_mock_ctx1.author.id)
    assert db_user.fetch_campaign_xp(campaign) == (15, 30, 1)
    db_trait = await CharacterTrait.get(trait.id)
    assert db_trait.value == 3


@pytest.mark.drop_db
async def test_xp_spend_not_enough_xp(
    async_mock_ctx1, mock_bot, user_factory, campaign_factory, trait_factory, character_factory
):
    """Test the cp_add command."""
    campaign = campaign_factory.build()
    await campaign.insert()

    # GIVEN a mock context, a user, a trait, and a campaign
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=5
    )
    await trait.insert()

    character = character_factory.build(traits=[trait], campaign=str(campaign.id))
    await character.insert()

    user = user_factory.build(
        id=async_mock_ctx1.author.id,
        characters=[character],
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=10, xp_total=30, cool_points=1)
        },
        macros=[],
    )
    await user.insert()

    # WHEN the xp_add command is called
    with pytest.raises(errors.NotEnoughExperienceError):
        await Experience(bot=mock_bot).xp_spend(
            async_mock_ctx1,
            async_mock_ctx1,
            trait=trait,
            hidden=False,
        )
