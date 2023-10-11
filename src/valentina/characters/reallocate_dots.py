"""A wizard that walks the user through the character creation process."""
import discord
from discord.ui import Button

from valentina.constants import EmbedColor, Emoji, TraitCategories
from valentina.models.db_tables import Character, Trait
from valentina.utils.helpers import get_max_trait_value
from valentina.views import IntegerButtons

## Dot Reallocation Wizard


class SelectTraitCategoryButtons(discord.ui.View):
    """Buttons to select a trait category."""

    def __init__(self, ctx: discord.ApplicationContext, character: Character):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.character = character
        self.cancelled: bool = False
        self.selected_category: TraitCategories = None

        # Create a button for each trait category
        all_trait_categories = [
            TraitCategories[trait.category.name] for trait in self.character.traits_list
        ]
        self.all_categories = list(set(all_trait_categories))

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

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a category."""
        await interaction.response.defer()
        # Disable the interaction and grab the setting name
        for child in self.children:
            if (
                isinstance(child, Button)
                and interaction.data.get("custom_id", None) == child.custom_id
            ):
                child.label = f"{Emoji.YES.value} {child.label}"

            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Return the selected character based on the custom_id of the button that was pressed
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected_category = self.all_categories[index]

        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        self.cancelled = True
        self.stop()


class SelectCharacterTraitButtons(discord.ui.View):
    """Buttons to select a specific trait."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        category: TraitCategories,
        positive_values_only: bool = False,
    ):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.positive_values_only = positive_values_only
        self.character = character
        self.category = category
        self.cancelled: bool = False
        self.selected_trait: Trait = None
        self.traits = [
            trait
            for trait in self.character.traits_list
            if trait.category.name == self.category.name
        ]

        # Create a button for each trait
        for i, trait in enumerate(self.traits):
            if self.positive_values_only and self.character.get_trait_value(trait) < 1:
                continue
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

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a trait."""
        await interaction.response.defer()
        # Disable the interaction and grab the setting name
        for child in self.children:
            if (
                isinstance(child, Button)
                and interaction.data.get("custom_id", None) == child.custom_id
            ):
                child.label = f"{Emoji.YES.value} {child.label}"

            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Return the selected character based on the custom_id of the button that was pressed
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected_trait = self.traits[index]
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        self.cancelled = True
        self.stop()


class ReallocateDots:
    """A wizard that walks the user through the process of reallocating dots."""

    def __init__(self, ctx: discord.ApplicationContext, character: Character):
        self.ctx = ctx
        self.character = character
        self.cancelled: bool = False
        self.trait_category: TraitCategories = None
        self.source_trait: Trait = None
        self.source_value: int = None
        self.target_trait: Trait = None
        self.target_value: int = None
        self.msg: discord.WebhookMessage = None

    async def execute(self) -> tuple[bool, Character]:
        """Start the wizard."""
        while not self.cancelled:
            self.trait_category = await self._get_category()
            self.source_trait, self.source_value = await self._get_source_trait()
            self.target_trait, self.target_value, self.max_value = await self._get_target_trait()
            num_dots = await self._num_dots()
            self.character = await self._reallocate(num_dots)
            return True, self.character

        return False, self.character

    async def _cancel(self, msg: str | None = None) -> None:
        """Cancel the wizard."""
        if not msg:
            msg = "Cancelled"

        embed = discord.Embed(
            title="Reallocate dots",
            description=f"{Emoji.CANCEL.value} {msg}",
            color=EmbedColor.WARNING.value,
        )
        await self.msg.edit(embed=embed, view=None)
        await self.msg.delete(delay=10.0)
        self.cancelled = True

    async def _get_category(self) -> TraitCategories:
        """Start the wizard."""
        view = SelectTraitCategoryButtons(self.ctx, self.character)
        embed = discord.Embed(
            title="Reallocate Dots",
            description="Select the **category** of the traits you want to reallocate",
            color=EmbedColor.INFO.value,
        )
        self.msg = await self.ctx.respond(embed=embed, view=view, ephemeral=True)  # type: ignore [assignment]
        await view.wait()

        if view.cancelled:
            await self._cancel()
            return None

        return view.selected_category

    async def _get_source_trait(self) -> tuple[Trait, int]:
        """Start the wizard."""
        view = SelectCharacterTraitButtons(
            self.ctx, self.character, self.trait_category, positive_values_only=True
        )
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"Select the {self.trait_category.name} **trait** you want to _take dots from_",
            color=EmbedColor.INFO.value,
        )
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        if view.cancelled:
            await self._cancel()
            return None

        self.source_trait = view.selected_trait
        self.source_value = self.character.get_trait_value(self.source_trait)

        if self.source_value == 0:
            await self._cancel(
                f"Cannot take dots from `{self.source_trait.name}` because it has no dots"
            )
            return None

        return self.source_trait, self.source_value

    async def _get_target_trait(self) -> tuple[Trait, int, int]:
        """Start the wizard."""
        view = SelectCharacterTraitButtons(self.ctx, self.character, self.trait_category)
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"{Emoji.SUCCESS.value} You are taking dots from `{self.source_trait.name}`\n\n**Select the **trait** you want to _add dots to_**",
            color=EmbedColor.INFO.value,
        )
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        if view.cancelled:
            await self._cancel()
            return None

        self.target_trait = view.selected_trait
        self.target_value = self.character.get_trait_value(self.target_trait)
        self.max_value = get_max_trait_value(self.target_trait.name, self.trait_category.name)

        if self.target_value >= self.max_value:
            await self._cancel(
                f"Cannot add dots to {self.target_trait.name} because it is maxed out"
            )
            return None

        return self.target_trait, self.target_value, self.max_value

    async def _num_dots(self) -> int:
        """Define the number of dots to reallocate."""
        available_dots = [
            i
            for i in range(1, self.source_value + 1)
            if (self.source_value - i >= 0) and (self.target_value + i <= self.max_value)
        ]

        if not available_dots:
            await self._cancel(
                f"Cannot add dots to {self.target_trait.name} because no dots are available"
            )
            return None

        if len(available_dots) == 1:
            return available_dots[0]

        view = IntegerButtons(available_dots)
        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"Select the number of dots to reallocate from `{self.source_trait.name}` to `{self.target_trait.name}`",  # noqa: S608
            color=EmbedColor.INFO.value,
        )
        await self.msg.edit(embed=embed, view=view)
        await view.wait()

        if view.cancelled:
            await self._cancel()
            return None

        return view.selection

    async def _reallocate(self, num_dots: int) -> Character:
        """Reallocate the dots."""
        self.character.set_trait_value(self.source_trait, self.source_value - num_dots)
        self.character.set_trait_value(self.target_trait, self.target_value + num_dots)

        embed = discord.Embed(
            title="Reallocate Dots",
            description=f"{Emoji.SUCCESS.value} Reallocated `{num_dots}` dots from `{self.source_trait.name}` to `{self.target_trait.name}`",
            color=EmbedColor.SUCCESS.value,
        )

        await self.msg.edit(embed=embed, view=None)
        await self.msg.delete(delay=10.0)

        return Character.get_by_id(self.character.id)
