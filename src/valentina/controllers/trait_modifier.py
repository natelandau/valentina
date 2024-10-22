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

    def _can_trait_be_upgraded(self, trait: CharacterTrait, amount: int = 1) -> bool:
        """Check if the trait can be upgraded.

        Args:
            trait (CharacterTrait): The trait to upgrade.
            amount (int): The amount of times to upgrade the trait. Defaults to 1.

        Returns:
            bool: True if the trait can be upgraded.
        """
        if trait.value + amount > trait.max_value:
            msg = "Trait is already at max value"
            raise errors.TraitAtMaxValueError(msg)

        return True

    def _can_trait_be_downgraded(self, trait: CharacterTrait, amount: int = 1) -> bool:
        """Check if the trait can be downgraded.

        Args:
            trait (CharacterTrait): The trait to downgrade.
            amount (int): The amount of times to downgrade the trait. Defaults to 1.

        Returns:
            bool: True if the trait can be downgraded.
        """
        if trait.value - amount < 0:
            msg = "Trait can not be lowered below 0"
            raise errors.TraitAtMinValueError(msg)

        return True

    async def _save_trait(self, trait: CharacterTrait) -> None:
        """Saves the updates to the trait and adds the trait to the character if it's not already there.

        Args:
            trait (CharacterTrait): The trait to add.
        """
        await trait.save()

        await self.character.fetch_all_links()
        await self.character.add_trait(character_trait=trait)

    def cost_to_upgrade(self, trait: CharacterTrait, amount: int = 1) -> int:
        """Calculate the cost to upgrade a trait.

        Args:
            trait (CharacterTrait): The trait to upgrade.
            amount (int): The amount of times to upgrade the trait. Defaults to 1.

        Returns:
            int: The cost to upgrade the trait.
        """
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.category.name)

        # Calculate the cost to upgrade the trait
        upgrade_cost = 0
        new_trait_value = trait.value
        for _ in range(amount):
            new_trait_value += 1
            if trait.max_value < new_trait_value:
                msg = "Trait can not be raised above max value"
                raise errors.TraitAtMaxValueError(msg)

            # First dots sometimes have a different cost so we need to check for that before just using the multiplier
            if new_trait_value == 0:
                upgrade_cost += get_trait_new_value(trait.name, trait.category.name)
            else:
                upgrade_cost += new_trait_value * multiplier

        return upgrade_cost

    def savings_from_downgrade(self, trait: CharacterTrait, amount: int = 1) -> int:
        """Calculate the savings from downgrading a trait.

        Args:
            trait (CharacterTrait): The trait to downgrade.
            amount (int): The amount of times to downgrade the trait. Defaults to 1.

        Returns:
            int: The savings from downgrading the trait.
        """
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.category.name)

        savings = 0
        new_trait_value = trait.value
        for _ in range(amount):
            if new_trait_value - 1 < 0:
                msg = "Trait can not be lowered below 0"
                raise errors.TraitAtMinValueError(msg)
            # First dots sometimes have a different cost so we need to check for that before just using the multiplier
            if new_trait_value == 0:
                savings += get_trait_new_value(trait.name, trait.category.name)
            else:
                savings += new_trait_value * multiplier
            new_trait_value -= 1

        return savings

    async def downgrade_with_freebie(
        self, trait: CharacterTrait, amount: int = 1
    ) -> CharacterTrait:
        """Downgrade a trait with freebie points.

        Args:
            trait (CharacterTrait): The trait to downgrade.
            amount (int): The amount of times to downgrade the trait. Defaults to 1.

        Returns:
            CharacterTrait: The downgraded trait.
        """
        if self._can_trait_be_downgraded(trait, amount):
            savings_from_downgrade = self.savings_from_downgrade(trait, amount)

            self.character.freebie_points = self.character.freebie_points + savings_from_downgrade
            trait.value = trait.value - amount

            await self.character.save()
            await self._save_trait(trait)

        return trait

    async def downgrade_with_xp(
        self, trait: CharacterTrait, campaign: "Campaign", amount: int = 1
    ) -> CharacterTrait:
        """Spend experience points to downgrade a trait.

        Args:
            trait (CharacterTrait): The trait to downgrade.
            campaign (Campaign): The campaign to spend experience points from.
            amount (int): The amount of times to downgrade the trait. Defaults to 1.

        Returns:
            CharacterTrait: The downgraded trait.
        """
        if self._can_trait_be_downgraded(trait, amount):
            savings_from_downgrade = self.savings_from_downgrade(trait, amount)

            await self.user.add_campaign_xp(
                campaign, savings_from_downgrade, increase_lifetime=False
            )
            trait.value = trait.value - amount
            await self._save_trait(trait)

        return trait

    async def upgrade_with_freebie(self, trait: CharacterTrait, amount: int = 1) -> CharacterTrait:
        """Upgrade a trait with freebie points.

        Args:
            trait (CharacterTrait): The trait to upgrade.
            amount (int): The amount of times to upgrade the trait. Defaults to 1.

        Returns:
            CharacterTrait: The upgraded trait.
        """
        self._can_trait_be_upgraded(trait, amount)

        cost_to_upgrade = self.cost_to_upgrade(trait, amount)

        if self.character.freebie_points < cost_to_upgrade:
            msg = "Not enough freebie points to upgrade trait"
            raise errors.NotEnoughFreebiePointsError(msg)

        self.character.freebie_points = self.character.freebie_points - cost_to_upgrade
        trait.value = trait.value + amount

        await self.character.save()
        await self._save_trait(trait)

        return trait

    async def upgrade_with_xp(
        self, trait: CharacterTrait, campaign: "Campaign", amount: int = 1
    ) -> CharacterTrait:
        """Spend experience points to upgrade a trait.

        Args:
            trait (CharacterTrait): The trait to upgrade.
            campaign (Campaign): The campaign to spend experience points from.
            amount (int): The amount of times to upgrade the trait. Defaults to 1.

        Returns:
            CharacterTrait: The upgraded trait.
        """
        self._can_trait_be_upgraded(trait, amount)

        cost_to_upgrade = self.cost_to_upgrade(trait, amount)

        await self.user.spend_campaign_xp(campaign, cost_to_upgrade)
        trait.value = trait.value + amount
        await self._save_trait(trait)

        return trait
