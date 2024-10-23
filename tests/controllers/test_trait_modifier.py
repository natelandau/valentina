# type: ignore
"""Tests for the TraitModifier controller."""

import pytest

from tests.factories import *
from valentina.constants import TraitCategory
from valentina.controllers import TraitModifier
from valentina.models.user import CampaignExperience
from valentina.utils import errors


@pytest.mark.drop_db
async def test_helper_functions(
    user_factory, campaign_factory, character_factory, trait_factory
) -> None:
    """Test the helper functions of the TraitModifier class."""
    # GIVEN a user, a campaign, a character, and a trait
    campaign = campaign_factory.build()
    # await campaign.insert()

    user = user_factory.build(
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=30, xp_total=30, cool_points=1)
        }
    )

    trait = trait_factory.build(
        category_name=TraitCategory.SKILLS.name, name="Drive", value=2, max_value=5
    )

    character = character_factory.build(traits=[trait])

    # WHEN the trait is upgraded with XP
    trait_modifier = TraitModifier(character=character, user=user)

    trait_modifier.can_trait_be_upgraded(trait)

    assert trait_modifier.cost_to_upgrade(trait) == 6
    assert trait_modifier.savings_from_downgrade(trait) == 4
    assert trait_modifier.can_trait_be_downgraded(trait)
    assert trait_modifier.can_trait_be_upgraded(trait)

    trait.value = 1
    assert trait_modifier.cost_to_upgrade(trait) == 4
    assert trait_modifier.cost_to_upgrade(trait, amount=2) == 10
    assert trait_modifier.cost_to_upgrade(trait, amount=4) == 28
    with pytest.raises(errors.TraitAtMaxValueError):
        assert trait_modifier.cost_to_upgrade(trait, amount=5)
    assert trait_modifier.savings_from_downgrade(trait) == 2
    with pytest.raises(errors.TraitAtMinValueError):
        assert trait_modifier.savings_from_downgrade(trait, amount=2)
    assert trait_modifier.can_trait_be_downgraded(trait)
    assert trait_modifier.can_trait_be_upgraded(trait)

    trait.value = 0
    assert trait_modifier.cost_to_upgrade(trait) == 2
    with pytest.raises(errors.TraitAtMinValueError):
        assert trait_modifier.savings_from_downgrade(trait)

    with pytest.raises(errors.TraitAtMinValueError):
        trait_modifier.can_trait_be_downgraded(trait)

    assert trait_modifier.can_trait_be_upgraded(trait)

    trait.value = 5
    with pytest.raises(errors.TraitAtMaxValueError):
        assert trait_modifier.cost_to_upgrade(trait)
    assert trait_modifier.savings_from_downgrade(trait) == 10
    with pytest.raises(errors.TraitAtMaxValueError):
        trait_modifier.can_trait_be_upgraded(trait)


@pytest.mark.drop_db
async def test_upgrade_with_xp(
    user_factory, campaign_factory, character_factory, trait_factory
) -> None:
    """Test upgrading a trait with XP."""
    # GIVEN a user, a campaign, a character, and a trait
    campaign = campaign_factory.build()

    user = user_factory.build(
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=30, xp_total=30, cool_points=1)
        }
    )

    trait = trait_factory.build(
        category_name=TraitCategory.SKILLS.name, name="Drive", value=2, max_value=5
    )
    character = character_factory.build(traits=[trait])

    # WHEN the trait is upgraded with XP
    trait_modifier = TraitModifier(character=character, user=user)
    upgraded_trait = await trait_modifier.upgrade_with_xp(trait, campaign)

    # THEN the trait should be upgraded
    assert upgraded_trait.value == 3
    assert user.fetch_campaign_xp(campaign) == (24, 30, 1)

    # WHEN a user does not have enough XP
    user.campaign_experience[str(campaign.id)].xp_current = 0

    # THEN an error should be raised
    with pytest.raises(errors.NotEnoughExperienceError):
        upgraded_trait = await trait_modifier.upgrade_with_xp(trait, campaign)


@pytest.mark.drop_db
async def test_downgrade_with_xp(
    user_factory, campaign_factory, character_factory, trait_factory
) -> None:
    """Test downgrading a trait with XP."""
    # GIVEN a user, a campaign, a character, and a trait
    campaign = campaign_factory.build()

    user = user_factory.build(
        campaign_experience={
            str(campaign.id): CampaignExperience(xp_current=30, xp_total=30, cool_points=1)
        }
    )

    trait = trait_factory.build(
        category_name=TraitCategory.SKILLS.name, name="Drive", value=2, max_value=5
    )
    character = character_factory.build(traits=[trait])

    # WHEN the trait is downgraded with XP
    trait_modifier = TraitModifier(character=character, user=user)
    downgraded_trait = await trait_modifier.downgrade_with_xp(trait, campaign)

    # THEN the trait should be downgraded
    assert downgraded_trait.value == 1
    assert user.fetch_campaign_xp(campaign) == (34, 30, 1)

    # WHEN the trait is at the minimum value
    trait.value = 0

    # THEN an error should be raised
    with pytest.raises(errors.TraitAtMinValueError):
        downgraded_trait = await trait_modifier.downgrade_with_xp(trait, campaign)


@pytest.mark.drop_db
async def test_upgrade_with_freebie(
    user_factory, campaign_factory, character_factory, trait_factory
) -> None:
    """Test upgrading a trait with Freebie points."""
    # GIVEN a user, a campaign, a character, and a trait

    user = user_factory.build()
    await user.insert()

    trait = trait_factory.build(
        category_name=TraitCategory.SKILLS.name, name="Drive", value=2, max_value=5
    )
    await trait.insert()
    character = character_factory.build(traits=[trait], freebie_points=20)
    await character.insert()

    # WHEN the trait is upgraded with XP
    trait_modifier = TraitModifier(character=character, user=user)
    upgraded_trait = await trait_modifier.upgrade_with_freebie(trait)

    # THEN the trait should be upgraded
    assert upgraded_trait.value == 3
    assert character.freebie_points == 14

    # WHEN the character does not have enough freebie points
    character.freebie_points = 0

    # THEN an error should be raised
    with pytest.raises(errors.NotEnoughFreebiePointsError):
        upgraded_trait = await trait_modifier.upgrade_with_freebie(trait)


@pytest.mark.drop_db
async def test_downgrade_with_freebie(
    user_factory, campaign_factory, character_factory, trait_factory
) -> None:
    """Test downgrading a trait with Freebie points."""
    # GIVEN a user, a campaign, a character, and a trait

    user = user_factory.build()
    await user.insert()

    trait = trait_factory.build(
        category_name=TraitCategory.SKILLS.name, name="Drive", value=2, max_value=5
    )
    await trait.insert()
    character = character_factory.build(traits=[trait], freebie_points=20)
    await character.insert()

    # WHEN the trait is downgraded with XP
    trait_modifier = TraitModifier(character=character, user=user)
    downgraded_trait = await trait_modifier.downgrade_with_freebie(trait)

    # THEN the trait should be downgraded
    assert downgraded_trait.value == 1
    assert character.freebie_points == 24

    # WHEN the trait is at the minimum value
    trait.value = 0

    # THEN an error should be raised
    with pytest.raises(errors.TraitAtMinValueError):
        downgraded_trait = await trait_modifier.downgrade_with_freebie(trait)
