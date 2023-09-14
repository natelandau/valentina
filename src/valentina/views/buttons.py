"""Buttons and views for Valentina."""
import discord
from discord.ui import Button

from valentina.constants import Emoji


class ReRollButton(discord.ui.View):
    """Add a re-roll button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(label="Re-Roll", style=discord.ButtonStyle.success, custom_id="reroll")
    async def reroll_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the re-roll button."""
        button.label += " ✅"
        button.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    @discord.ui.button(label="Done", style=discord.ButtonStyle.secondary, custom_id="done")
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the re-roll button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True

        if self.author.guild_permissions.administrator:  # type: ignore
            return True

        return interaction.user.id == self.author.id


class ConfirmCancelButtons(discord.ui.View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
    )
    async def cancel_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the cancel button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id


class CancelButton(discord.ui.View):
    """Add a cancel button to an interaction."""

    def __init__(self, ctx: discord.ApplicationContext):
        super().__init__()
        self.ctx = ctx
        self.confirmed: bool = None

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
    )
    async def cancel_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the cancel button."""
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=self)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id
