"""A wizard to spend experience and freebie points."""

from typing import cast

import discord

from valentina.constants import (
    CharClassType,
    EmbedColor,
    Emoji,
    TraitCategories,
    VampireClanType,
    XPMultiplier,
)
from valentina.models.bot import Valentina
from valentina.models.sqlite_models import Character, Trait
from valentina.utils.helpers import get_max_trait_value, get_trait_multiplier, get_trait_new_value

from .buttons import SelectCharacterTraitButtons, SelectTraitCategoryButtons


class SpendFreebiePoints(discord.ui.View):
    """Guide the user through spending freebie points."""

    # TODO: Add merits/flaws/backgrounds or other areas not on sheet

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
    ):
        self.ctx = ctx
        self.bot = cast(Valentina, ctx.bot)
        self.character = character
        self.char_class = CharClassType[character.char_class.name]

        # Character and traits attributes
        self.trait_category: TraitCategories = None
        self.trait: Trait = None
        self.value: int = None
        self.cost: int = None

        # Wizard state
        self.msg: discord.WebhookMessage = None
        self.cancelled: bool = False

    async def start_wizard(self) -> tuple[bool, Character]:
        """Start the wizard."""
        # Prompt user for trait category
        self.trait_category = await self._prompt_for_trait_category()

        # Prompt the user for the trait they want to add dots to
        self.trait, self.value = await self._prompt_for_source_trait()

        # Add a dot to the selected trait
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

    async def _prompt_for_trait_category(self) -> TraitCategories:
        """Terminate the reallocation wizard and inform the user.

        This method updates the Discord embed with a cancellation message, deletes the embed after a short delay, and sets the internal state as cancelled.

        Args:
            msg (str | None): Optional custom message for the cancellation. If not provided, a default is used.
        """
        # Exit early if the wizard is already cancelled
        if self.cancelled:
            return None

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

    async def _prompt_for_source_trait(self) -> tuple[Trait, int]:
        """Prompt the user to choose a trait from which dots will be taken.

        If the user cancels the selection or if the chosen trait has no dots, the wizard is cancelled.

        Returns:
            tuple (Trait, int): The selected source trait and its current value, or None if cancelled or if trait has no dots.
        """
        # Exit early if the wizard is already cancelled
        if self.cancelled:
            return None

        # Determine the traits that can be used as a target
        available_traits = [
            trait
            for trait in self.character.traits_list
            if trait.category.name == self.trait_category.name
            and self.character.get_trait_value(trait)
            < get_max_trait_value(trait.name, self.trait_category.name)
        ]

        # Set up the view and embed to prompt the user to select a trait
        view = SelectCharacterTraitButtons(self.ctx, self.character, traits=available_traits)
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

        # Store the user's trait selection and its current value
        self.trait = view.selected_trait
        self.value = self.character.get_trait_value(self.trait)

        return self.trait, self.value

    async def _add_dot(self) -> Character:
        """Add a dot to the selected trait."""
        # Exit early if the wizard is already cancelled
        if self.cancelled:
            return None

        # Compute the cost of the upgrade

        # Find vampire clan disciplines
        if self.char_class == CharClassType.VAMPIRE:
            clan = VampireClanType[self.character.clan.name]

            # Get the multiplier for the trait
            if self.trait.name in clan.value["disciplines"]:
                multiplier = XPMultiplier.CLAN_DISCIPLINE.value
            else:
                multiplier = get_trait_multiplier(self.trait.name, self.trait_category.name)
        else:
            multiplier = get_trait_multiplier(self.trait.name, self.trait_category.name)

        if self.value == 0:
            self.upgrade_cost = get_trait_new_value(self.trait.name, self.trait_category.name)
        else:
            self.upgrade_cost = (self.value + 1) * multiplier

        # Guard statement, cannot spend more points than available
        if self.upgrade_cost >= self.character.freebie_points:
            await self._cancel_wizard(
                msg=f"Not enough freebie points, can not update `{self.trait.name}`.\n\nNeeded `{self.upgrade_cost}` and you have `{self.character.freebie_points}` freebie points remaining."
            )
            return None

        # Make the database changes
        self.character.data["freebie_points"] -= self.upgrade_cost
        self.character.save()
        self.character.set_trait_value(self.trait, self.value + 1)

        # Compute conviction, humanity, and willpower
        if self.trait in [
            Trait.get(name="Courage"),
            Trait.get(name="Self-Control"),
            Trait.get(name="Zeal"),
            Trait.get(name="Vision"),
        ]:
            willpower = self.character.get_trait_value(Trait.get(name="Willpower"))
            self.character.set_trait_value(Trait.get(name="Willpower"), willpower + 1)
        if self.trait == Trait.get(name="Conscience"):
            humanity = self.character.get_trait_value(Trait.get(name="Humanity"))
            self.character.set_trait_value(Trait.get(name="Humanity"), humanity + 1)
        if self.trait == Trait.get(name="Mercy"):
            conviction = self.character.get_trait_value(Trait.get(name="Conviction"))
            self.character.set_trait_value(Trait.get(name="Conviction"), conviction + 1)

        self.bot.user_svc.purge_cache(self.ctx)

        # Return the result based on the state of self.cancelled
        return Character.get_by_id(self.character.id)
