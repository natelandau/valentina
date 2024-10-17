"""Manage buying traits with freebie points or experience."""

from typing import TYPE_CHECKING

from valentina.constants import TraitCategory, XPMultiplier
from valentina.models import Character, CharacterTrait, User
from valentina.utils import errors
from valentina.utils.helpers import get_trait_multiplier, get_trait_new_value

if TYPE_CHECKING:
    from valentina.models import Campaign


class TraitModifier:
    """Manage the purchase of traits with freebie points or experience."""

    def __init__(self, character: Character, user: User) -> None:
        self.character = character
        self.user = user

    def _can_trait_be_upgraded(self, trait: CharacterTrait) -> bool:
        """Check if the trait can be upgraded."""
        if trait.value >= trait.max_value:
            msg = "Trait is already at max value"
            raise errors.TraitAtMaxValueError(msg)

        return True

    def _can_trait_be_downgraded(self, trait: CharacterTrait) -> bool:
        """Check if the trait can be downgraded."""
        return trait.value > 0

    def cost_to_upgrade(self, trait: CharacterTrait) -> int:
        """Get the cost to upgrade a trait."""
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.category.name)

        # First dots sometimes have a different cost so we need to check for that before just using the multiplier
        if trait.value == 0:
            upgrade_cost = get_trait_new_value(trait.name, trait.category.name)
        else:
            upgrade_cost = (trait.value + 1) * multiplier

        return upgrade_cost

    def savings_from_downgrade(self, trait: CharacterTrait) -> int:
        """Get the savings from downgrading a trait."""
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.category.name)

        # First dots sometimes have a different cost so we need to check for that before just using the multiplier
        if trait.value == 1:
            savings = get_trait_new_value(trait.name, trait.category.name)
        else:
            savings = trait.value * multiplier

        return savings

    async def upgrade_with_xp(self, trait: CharacterTrait, campaign: "Campaign") -> CharacterTrait:
        """Spend experience points to upgrade a trait."""
        self._can_trait_be_upgraded(trait)

        cost_to_upgrade = self.cost_to_upgrade(trait)

        await self.user.spend_campaign_xp(campaign, cost_to_upgrade)
        trait.value = trait.value + 1
        await trait.save()

        return trait

    async def downgrade_with_xp(
        self, trait: CharacterTrait, campaign: "Campaign"
    ) -> CharacterTrait:
        """Spend experience points to downgrade a trait."""
        if self._can_trait_be_downgraded(trait):
            savings_from_downgrade = self.savings_from_downgrade(trait)

            await self.user.add_campaign_xp(
                campaign, savings_from_downgrade, increase_lifetime=False
            )
            trait.value = trait.value - 1
            await trait.save()

        return trait

    async def upgrade_with_freebie(self, trait: CharacterTrait) -> CharacterTrait:
        """Upgrade a trait with freebie points."""
        self._can_trait_be_upgraded(trait)

        cost_to_upgrade = self.cost_to_upgrade(trait)

        if self.character.freebie_points < cost_to_upgrade:
            msg = "Not enough freebie points to upgrade trait"
            raise errors.NotEnoughFreebiePointsError(msg)

        self.character.freebie_points = self.character.freebie_points - cost_to_upgrade
        trait.value = trait.value + 1

        await self.character.save()
        await trait.save()

        return trait

    async def downgrade_with_freebie(self, trait: CharacterTrait) -> CharacterTrait:
        """Downgrade a trait with freebie points."""
        if self._can_trait_be_downgraded(trait):
            savings_from_downgrade = self.savings_from_downgrade(trait)

            self.character.freebie_points = self.character.freebie_points + savings_from_downgrade
            trait.value = trait.value - 1

            await self.character.save()
            await trait.save()

        return trait
