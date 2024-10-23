"""A wizard that walks the user through the character creation process."""

from typing import cast

import discord

from valentina.constants import EmbedColor, Emoji, TraitCategory
from valentina.discord.bot import ValentinaContext
from valentina.discord.views import IntegerButtons
from valentina.models import Character, CharacterTrait

from .buttons import SelectCharacterTraitButtons, SelectTraitCategoryButtons


class DotsReallocationWizard:
    """Guide the user through the process of reallocating trait dots for a character.

    The wizard interacts with the user using Discord embeds and buttons. The process involves:
    - Choosing the trait category.
    - Selecting the source trait (from where dots will be taken).
    - Selecting the target trait (to where dots will be added).
    - Specifying the number of dots to reallocate.
    - Executing the reallocation and updating the character's trait values.
    """

    def __init__(self, ctx: ValentinaContext, character: Character):
        self.ctx = ctx
        self.character = character

        # Character and traits attributes
        self.category: TraitCategory = None
        self.source: CharacterTrait = None
        self.target: CharacterTrait = None

        # Wizard state
        self.msg: discord.WebhookMessage = None
        self.cancelled: bool = False

    async def start_wizard(self) -> tuple[bool, Character]:
        """Launch the dot reallocation wizard to guide the user through the process.

            The method progresses through several steps:
            - Choosing the trait category.
            - Selecting the source trait.
            - Selecting the target trait.
            - Specifying the number of dots to reallocate.
            - Executing the reallocation.

            The wizard terminates if the user cancels at any step or upon completion.

        Returns:
            tuple (bool, Character): A boolean indicating if the reallocation was successful, and the updated character object.
        """
        # Prompt user for trait category
        if not self.cancelled:
            self.category = await self._prompt_for_category()

        # Prompt user for source trait and its value
        if not self.cancelled:
            self.source = await self._prompt_for_source()

        # Prompt user for target trait, its value, and its maximum allowable value
        if not self.cancelled:
            self.target = await self._prompt_for_target()

        # Ask user the number of dots they want to reallocate
        if not self.cancelled:
            num_dots = await self._prompt_for_dots_to_reallocate()

        # Perform the reallocation
        if not self.cancelled:
            self.character = await self._reallocate(num_dots)

        # Return the result based on the state of self.cancelled
        return (not self.cancelled, self.character)

    async def _cancel_wizard(self, msg: str | None = None) -> None:
        """Cancel the wizard."""
        if not msg:
            msg = "Cancelled"

        embed = discord.Embed(
            title="Reallocate dots",
            description=f"{Emoji.CANCEL.value} {msg}",
            color=EmbedColor.WARNING.value,
        )
        await self.msg.edit(embed=embed, view=None)
        await self.msg.delete(delay=5.0)
        self.cancelled = True

    async def _prompt_for_category(self) -> TraitCategory:
        """Terminate the reallocation wizard and inform the user.

        This method updates the Discord embed with a cancellation message, deletes the embed after a short delay, and sets the internal state as cancelled.

        Args:
            msg (str | None): Optional custom message for the cancellation. If not provided, a default is used.
        """
        # Set up the view and embed to prompt the user to select a trait category
        view = SelectTraitCategoryButtons(self.ctx, self.character)
        embed = discord.Embed(
            title="Reallocate Dots",
            description="Select the **category** of the traits you want to reallocate",
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

    async def _prompt_for_source(self) -> CharacterTrait:
        """Prompt the user to choose a trait from which dots will be taken.

        If the user cancels the selection or if the chosen trait has no dots, the wizard is cancelled.

        Returns:
            CharacterTrait: The trait the user chose.
        """
        # Determine the traits that can be used as a source
        # Determine the traits that can be used as a target
        available_traits = [
            trait
            for trait in cast(list[CharacterTrait], self.character.traits)
            if trait.trait_category == self.category and trait.value > 0
        ]

        # Set up the view and embed to prompt the user to select a trait
        view = SelectCharacterTraitButtons(self.ctx, traits=available_traits)
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"Select the {self.category.name} **trait** you want to _take dots from_",
            color=EmbedColor.INFO.value,
        )

        # Show the embed to the user and wait for their response
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        # Handle user cancellation
        if view.cancelled:
            await self._cancel_wizard()
            return None

        return view.selected_trait

    async def _prompt_for_target(self) -> CharacterTrait:
        """Prompt the user to choose a trait to which dots will be added.

        After user selection, the method verifies if the chosen trait has reached its maximum value.  If so, the wizard is cancelled.

        Returns:
            tuple: The selected target trait, its current value, and its max value.
            None if the wizard is cancelled or if the trait is maxed out.
        """
        # Determine the traits that can be used as a target
        available_traits = [
            trait
            for trait in cast(list[CharacterTrait], self.character.traits)
            if trait.trait_category == self.category and trait.value < trait.max_value
        ]

        # Set up the view and embed to prompt the user to select a trait
        view = SelectCharacterTraitButtons(self.ctx, traits=available_traits)
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"{Emoji.SUCCESS.value} You are taking dots from `{self.source.name}`\n\n**Select the **trait** you want to _add dots to_**",
            color=EmbedColor.INFO.value,
        )

        # Show the embed to the user and wait for their response
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        # Handle user cancellation
        if view.cancelled:
            await self._cancel_wizard()
            return None

        # Store the user's trait selection and its current value and max value
        return view.selected_trait

    async def _prompt_for_dots_to_reallocate(self) -> int:
        """Prompt the user to select the quantity of dots to reallocate from the source to the target trait.

        The method calculates the available dots based on the source's current value and the target's max allowed value. If only one dot is available, that value is automatically chosen. Otherwise, the user is presented with a range of valid choices.

        Returns:
            int: The number of dots chosen for reallocation, or None if the process is cancelled or no dots are available.
        """
        # Determine the number of dots that can be reallocated
        available_dots = [
            i
            for i in range(1, self.source.value + 1)
            if (self.source.value - i >= 0) and (self.target.value + i <= self.target.max_value)
        ]

        # If no dots are available, cancel the wizard and inform the user
        if not available_dots:
            await self._cancel_wizard(
                f"Cannot add dots to {self.target.name} because no dots are available"
            )
            return None

        # If only one dot is available, return it
        if len(available_dots) == 1:
            return available_dots[0]

        # Otherwise, prompt the user to select the number of dots to reallocate
        view = IntegerButtons(available_dots)
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"Select the number of dots to reallocate from `{self.source.name}` to `{self.target.name}`",  # noqa: S608
            color=EmbedColor.INFO.value,
        )
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        # Handle user cancellation
        if view.cancelled:
            await self._cancel_wizard()
            return None

        return view.selection

    async def _reallocate(self, num_dots: int) -> Character:
        """Reallocate a specified number of dots from the source trait to the target trait and update the character data.

        This method performs the following steps:
        1. Updates the character's traits in memory.
        2. Notifies the user of the successful reallocation using an embed.
        3. Fetches and returns the updated character from the database.

        Args:
            num_dots (int): The number of dots to be reallocated.

        Returns:
            Character: The updated character after reallocation.
        """
        # Exit early if the wizard is already cancelled
        if self.cancelled:
            return None

        # Update the character's trait values in the database
        self.source.value -= num_dots
        self.target.value += num_dots
        await self.source.save()
        await self.target.save()
        await self.character.save()

        # Update the embed to inform the user of the success
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"{Emoji.SUCCESS.value} Reallocated `{num_dots}` dots from `{self.source.name}` to `{self.target.name}`",
            color=EmbedColor.SUCCESS.value,
        )
        await self.msg.edit(embed=embed, view=None)

        # Delete the embed after a short delay
        await self.msg.delete(delay=5.0)

        return await Character.get(self.character.id, fetch_links=True)
