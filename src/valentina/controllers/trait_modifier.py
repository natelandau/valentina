"""Manage buying traits with freebie points or experience."""

from typing import TYPE_CHECKING

from valentina.constants import TraitCategory, XPMultiplier
from valentina.models import Character, CharacterTrait, User
from valentina.utils import errors
from valentina.utils.helpers import get_trait_multiplier, get_trait_new_value

if TYPE_CHECKING:
    from valentina.models import Campaign


class TraitModifier:
    """Manage the purchase and modification of character traits using freebie points or experience.

    This class provides methods to upgrade, downgrade, and validate trait modifications
    for a given character, handling both freebie point and experience point transactions.

    Attributes:
        character (Character): The character whose traits are being modified.
        user (User): The user associated with the character.
    """

    def __init__(self, character: Character, user: User) -> None:
        self.character = character
        self.user = user

    def can_trait_be_upgraded(self, trait: CharacterTrait, amount: int = 1) -> bool:
        """Check if a trait can be upgraded by the specified amount.

        Args:
            trait (CharacterTrait): The trait to upgrade.
            amount (int): The amount of times to upgrade the trait. Defaults to 1.

        Returns:
            bool: True if the trait can be upgraded, False otherwise.

        Raises:
            errors.TraitAtMaxValueError: If upgrading would exceed the trait's maximum value.
        """
        if trait.value + amount > trait.max_value:
            msg = "Trait is already at max value"
            raise errors.TraitAtMaxValueError(msg)

        return True

    def can_trait_be_downgraded(self, trait: CharacterTrait, amount: int = 1) -> bool:
        """Check if a trait can be downgraded by the specified amount.

        Args:
            trait (CharacterTrait): The trait to downgrade.
            amount (int): The amount of times to downgrade the trait. Defaults to 1.

        Returns:
            bool: True if the trait can be downgraded, False otherwise.

        Raises:
            errors.TraitAtMinValueError: If downgrading would result in a negative trait value.
        """
        if trait.value - amount < 0:
            msg = "Trait can not be lowered below 0"
            raise errors.TraitAtMinValueError(msg)

        return True

    async def _save_trait(self, trait: CharacterTrait) -> CharacterTrait:
        """Save updates to a trait and ensure it's properly linked to the character.

        This method fetches all character links, adds the trait to the character,
        and saves the changes.

        Args:
            trait (CharacterTrait): The trait to be saved and linked.

        Returns:
            CharacterTrait: The saved and linked trait.

        Raises:
            errors.TraitExistsError: If the trait already exists for the character.
        """
        await self.character.fetch_all_links()
        await self.character.add_trait(trait)
        return trait

    def cost_to_upgrade(self, trait: CharacterTrait, amount: int = 1) -> int:
        """Calculate the cost to upgrade a trait by the specified amount.

        This method takes into account special cases such as clan disciplines
        and varying costs for different trait levels.

        Args:
            trait (CharacterTrait): The trait to be upgraded.
            amount (int, optional): The number of levels to upgrade. Defaults to 1.

        Returns:
            int: The total cost to upgrade the trait.

        Raises:
            errors.TraitAtMaxValueError: If upgrading would exceed the trait's maximum value.
        """
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.trait_category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.trait_category.name)

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
                upgrade_cost += get_trait_new_value(trait.name, trait.trait_category.name)
            else:
                upgrade_cost += new_trait_value * multiplier

        return upgrade_cost

    def savings_from_downgrade(self, trait: CharacterTrait, amount: int = 1) -> int:
        """Calculate the points saved from downgrading a trait by the specified amount.

        This method considers special cases such as clan disciplines and varying
        costs for different trait levels.

        Args:
            trait (CharacterTrait): The trait to be downgraded.
            amount (int, optional): The number of levels to downgrade. Defaults to 1.

        Returns:
            int: The total points saved from downgrading the trait.

        Raises:
            errors.TraitAtMinValueError: If downgrading would result in a negative trait value.
        """
        # Find the multiplier for the trait. Because vampires get a discount on their own class' disciplines, we need to check for that.
        if (
            trait.trait_category == TraitCategory.DISCIPLINES
            and self.character.clan
            and trait.name in self.character.clan.value.disciplines
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.trait_category.name)

        savings = 0
        new_trait_value = trait.value
        for _ in range(amount):
            if new_trait_value - 1 < 0:
                msg = "Trait can not be lowered below 0"
                raise errors.TraitAtMinValueError(msg)
            # First dots sometimes have a different cost so we need to check for that before just using the multiplier
            if new_trait_value == 0:
                savings += get_trait_new_value(trait.name, trait.trait_category.name)
            else:
                savings += new_trait_value * multiplier
            new_trait_value -= 1

        return savings

    async def downgrade_with_freebie(
        self, trait: CharacterTrait, amount: int = 1
    ) -> CharacterTrait:
        """Downgrade a trait using freebie points.

        This method checks if the downgrade is possible, calculates the savings,
        updates the character's freebie points, and saves the changes.

        Args:
            trait (CharacterTrait): The trait to be downgraded.
            amount (int, optional): The number of levels to downgrade. Defaults to 1.

        Returns:
            CharacterTrait: The downgraded trait.

        Raises:
            errors.TraitAtMinValueError: If downgrading would result in a negative trait value.
        """
        if self.can_trait_be_downgraded(trait, amount):
            savings_from_downgrade = self.savings_from_downgrade(trait, amount)

            self.character.freebie_points = self.character.freebie_points + savings_from_downgrade
            trait.value = trait.value - amount

            await self.character.save()
            await self._save_trait(trait)

        return trait

    async def downgrade_with_xp(
        self, trait: CharacterTrait, campaign: "Campaign", amount: int = 1
    ) -> CharacterTrait:
        """Downgrade a trait using experience points.

        This method checks if the downgrade is possible, calculates the savings,
        adds the experience points to the user's campaign, and saves the changes.

        Args:
            trait (CharacterTrait): The trait to be downgraded.
            campaign (Campaign): The campaign associated with the experience points.
            amount (int, optional): The number of levels to downgrade. Defaults to 1.

        Returns:
            CharacterTrait: The downgraded trait.

        Raises:
            errors.TraitAtMinValueError: If downgrading would result in a negative trait value.
        """
        if self.can_trait_be_downgraded(trait, amount):
            savings_from_downgrade = self.savings_from_downgrade(trait, amount)

            await self.user.add_campaign_xp(
                campaign, savings_from_downgrade, increase_lifetime=False
            )
            trait.value = trait.value - amount
            await self._save_trait(trait)

        return trait

    async def upgrade_with_freebie(self, trait: CharacterTrait, amount: int = 1) -> CharacterTrait:
        """Upgrade a trait using freebie points.

        This method checks if the upgrade is possible, calculates the cost,
        deducts the freebie points from the character, and saves the changes.

        Args:
            trait (CharacterTrait): The trait to be upgraded.
            amount (int, optional): The number of levels to upgrade. Defaults to 1.

        Returns:
            CharacterTrait: The upgraded trait.

        Raises:
            errors.TraitAtMaxValueError: If upgrading would exceed the trait's maximum value.
            errors.NotEnoughFreebiePointsError: If the character doesn't have enough freebie points.
        """
        self.can_trait_be_upgraded(trait, amount)

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
        """Upgrade a trait using experience points.

        This method checks if the upgrade is possible, calculates the cost,
        spends the experience points from the user's campaign, and saves the changes.

        Args:
            trait (CharacterTrait): The trait to be upgraded.
            campaign (Campaign): The campaign associated with the experience points.
            amount (int, optional): The number of levels to upgrade. Defaults to 1.

        Returns:
            CharacterTrait: The upgraded trait.

        Raises:
            errors.TraitAtMaxValueError: If upgrading would exceed the trait's maximum value.
            errors.NotEnoughXPError: If the user doesn't have enough experience points in the campaign.
        """
        self.can_trait_be_upgraded(trait, amount)

        cost_to_upgrade = self.cost_to_upgrade(trait, amount)

        await self.user.spend_campaign_xp(campaign, cost_to_upgrade)
        trait.value = trait.value + amount
        await self._save_trait(trait)

        return trait
