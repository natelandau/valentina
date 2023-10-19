"""Buttons for character creation."""
import discord
from discord.ui import Button

from valentina.constants import Emoji, TraitCategories
from valentina.models.sqlite_models import Character, Trait


class SelectTraitCategoryButtons(discord.ui.View):
    """Buttons to select a trait category."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
    ):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.character = character
        self.cancelled: bool = False
        self.selected_category: TraitCategories = None

        # Create a button for each trait category
        all_trait_categories = [
            TraitCategories[trait.category.name] for trait in self.character.traits_list
        ]
        self.all_categories = sorted(set(all_trait_categories), key=lambda x: x.value["order"])

        # Create a button for each category
        for i, category in enumerate(self.all_categories):
            button: Button = Button(
                label=f"{i + 1}. {category.name.title()}",
                custom_id=f"{i}",
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

        cancel_button: Button = Button(
            label=f"{Emoji.CANCEL.value} Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel",
        )
        cancel_button.callback = self.cancel_callback  # type: ignore [method-assign]
        self.add_item(cancel_button)

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a category."""
        await interaction.response.defer()
        # Disable the interaction and grab the setting name
        self._disable_all()

        # Return the selected character based on the custom_id of the button that was pressed
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected_category = self.all_categories[index]

        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.cancelled = True
        self.stop()


class SelectCharacterTraitButtons(discord.ui.View):
    """Buttons to select a specific trait."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        traits: list[Trait],
        not_maxed_only: bool = False,
    ):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.not_maxed_only = not_maxed_only
        self.character = character
        self.cancelled: bool = False
        self.selected_trait: Trait = None
        self.traits = traits

        # Create a button for each trait
        for i, trait in enumerate(self.traits):
            # Add the button
            button: Button = Button(
                label=f"{i + 1}. {trait.name.title()}",
                custom_id=f"{i}",
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

        cancel_button: Button = Button(
            label=f"{Emoji.CANCEL.value} Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel",
        )
        cancel_button.callback = self.cancel_callback  # type: ignore [method-assign]
        self.add_item(cancel_button)

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a trait."""
        await interaction.response.defer()
        self._disable_all()

        # Return the selected character based on the custom_id of the button that was pressed
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected_trait = self.traits[index]
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.cancelled = True
        self.stop()
