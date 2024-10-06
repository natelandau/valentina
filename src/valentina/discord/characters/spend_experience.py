"""A wizard to spend experience and freebie points."""

from typing import cast

import discord

from valentina.constants import (
    CharClass,
    EmbedColor,
    Emoji,
    TraitCategory,
    XPMultiplier,
)
from valentina.discord.bot import ValentinaContext
from valentina.models import Character, CharacterTrait
from valentina.utils.helpers import get_trait_multiplier, get_trait_new_value

from .buttons import SelectCharacterTraitButtons, SelectTraitCategoryButtons


class SpendFreebiePoints(discord.ui.View):
    """Guide the user through the process of spending freebie points on character traits.

    This class provides a wizard-like interface for users to allocate their
    character's freebie points to various traits. It handles the selection of
    trait categories, individual traits, and the allocation of points.

    Attributes:
        ctx (ValentinaContext): The context of the Discord application.
        character (Character): The character on which freebie points are being spent.
        trait_category (TraitCategory): The selected category of traits.
        trait (CharacterTrait): The specific trait selected for point allocation.
        msg (discord.WebhookMessage): The message used for user interaction.
        cancelled (bool): Flag indicating if the wizard process was cancelled.

    """

    # TODO: Add merits/flaws/backgrounds or other areas not on sheet

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
    ):
        self.ctx = ctx
        self.character = character

        # Character and traits attributes
        self.trait_category: TraitCategory = None
        self.trait: CharacterTrait = None

        # Wizard state
        self.msg: discord.WebhookMessage = None
        self.cancelled: bool = False

    async def start_wizard(self) -> tuple[bool, Character]:
        """Start the wizard."""
        # Prompt user for trait category
        if not self.cancelled:
            self.trait_category = await self._prompt_for_trait_category()

        # Prompt the user for the trait they want to add dots to
        if not self.cancelled:
            self.trait = await self._prompt_for_trait()

        # Add a dot to the selected trait and update the character
        if not self.cancelled:
            self.character = await self._add_dot()

            # Update the embed to inform the user of the success
            embed = discord.Embed(
                title="Reallocate Dots",
                description=f"{Emoji.SUCCESS.value} Added 1 dot to {self.trait.name} for `{self.upgrade_cost}` freebie points.\n\nYou have `{self.character.freebie_points}` freebie points remaining.",
                color=EmbedColor.SUCCESS.value,
            )
            await self.msg.edit(embed=embed, view=None)

            # Delete the embed after a short delay
            await self.msg.delete(delay=5.0)

        # Return the result based on the state of self.cancelled
        return (not self.cancelled, self.character)

    async def _cancel_wizard(self, msg: str | None = None) -> None:
        """Cancel the wizard."""
        if not msg:
            msg = "Cancelled"

        embed = discord.Embed(
            title="Spend Freebie Points",
            description=f"{Emoji.CANCEL.value} {msg}",
            color=EmbedColor.WARNING.value,
        )
        await self.msg.edit(embed=embed, view=None)
        await self.msg.delete(delay=5.0)
        self.cancelled = True

    async def _prompt_for_trait_category(self) -> TraitCategory:
        """Terminate the reallocation wizard and inform the user.

        This method updates the Discord embed with a cancellation message, deletes the embed after a short delay, and sets the internal state as cancelled.

        Args:
            msg (str | None): Optional custom message for the cancellation. If not provided, a default is used.
        """
        # Set up the view and embed to prompt the user to select a trait category
        view = SelectTraitCategoryButtons(self.ctx, self.character)
        embed = discord.Embed(
            title="Spend Freebie Points",
            description="Select the **category** of the traits you want to add dots to",
            color=EmbedColor.INFO.value,
        )

        # Show the embed to the user and wait for their response
        self.msg = await self.ctx.respond(embed=embed, view=view, ephemeral=True)  # type: ignore [assignment]
        await view.wait()

        # Handle user cancellation
        if view.cancelled:
            await self._cancel_wizard()
            return None

        return view.selected_category

    async def _prompt_for_trait(self) -> CharacterTrait:
        """Prompt the user to choose a trait to add dots to.

        If the user cancels the selection or if the chosen trait has no dots, the wizard is cancelled.

        Returns:
            CharacterTrait: The trait the user chose.
        """
        # Determine the traits that can be used as a target
        available_traits = [
            trait
            for trait in cast(list[CharacterTrait], self.character.traits)
            if trait.category == self.trait_category and trait.value < trait.max_value
        ]

        # Set up the view and embed to prompt the user to select a trait
        view = SelectCharacterTraitButtons(self.ctx, traits=available_traits)
        embed = discord.Embed(
            title="Spend Freebie Points",
            description=f"Select the trait in {self.trait_category.name.title()} you want to increase",
            color=EmbedColor.INFO.value,
        )

        # Show the embed to the user and wait for their response
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        # Handle user cancellation
        if view.cancelled:
            await self._cancel_wizard()
            return None

        # Store the user's trait selection
        return view.selected_trait

    async def _add_dot(self) -> Character:
        """Add a dot to the selected trait."""
        # Compute the cost of the upgrade

        # Find vampire clan disciplines
        if self.character.char_class == CharClass.VAMPIRE:
            # Get the multiplier for the trait
            if self.trait.name in self.character.clan.value.disciplines:
                multiplier = XPMultiplier.CLAN_DISCIPLINE.value
            else:
                multiplier = get_trait_multiplier(self.trait.name, self.trait_category.name)
        else:
            multiplier = get_trait_multiplier(self.trait.name, self.trait_category.name)

        if self.trait.value == 0:
            self.upgrade_cost = get_trait_new_value(self.trait.name, self.trait_category.name)
        else:
            self.upgrade_cost = (self.trait.value + 1) * multiplier

        # Guard statement, cannot spend more points than available
        if self.upgrade_cost >= self.character.freebie_points:
            await self._cancel_wizard(
                msg=f"Not enough freebie points, can not update `{self.trait.name}`.\n\nNeeded `{self.upgrade_cost}` and you have `{self.character.freebie_points}` freebie points remaining."
            )
            return None

        # Make the database changes
        self.character.freebie_points -= self.upgrade_cost
        self.trait.value += 1
        await self.trait.save()
        await self.character.save()

        return await Character.get(self.character.id, fetch_links=True)
