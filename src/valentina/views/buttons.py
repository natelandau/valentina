"""Buttons and views for Valentina."""
import discord
from discord import Interaction
from discord.ui import Button, View


class ReRollButton(View):
    """Add a re-roll button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(label="Re-Roll", style=discord.ButtonStyle.success, custom_id="reroll")
    async def reroll_callback(self, button: Button, interaction: Interaction) -> None:
        """Callback for the re-roll button."""
        button.label += " ✅"
        button.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    @discord.ui.button(label="Done", style=discord.ButtonStyle.secondary, custom_id="done")
    async def done_callback(self, button: Button, interaction: Interaction) -> None:
        """Callback for the re-roll button."""
        button.label += " ✅"
        button.disabled = True
        for child in self.children:
            if type(child) == Button:
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True

        if self.author.guild_permissions.administrator:  # type: ignore
            return True

        return interaction.user.id == self.author.id


class ConfirmCancelButtons(View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
    async def confirm_callback(self, button: Button, interaction: Interaction) -> None:
        """Callback for the confirm button."""
        button.label += " ✅"
        button.disabled = True
        for child in self.children:
            if type(child) == Button:
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")
    async def cancel_callback(self, button: Button, interaction: Interaction) -> None:
        """Callback for the cancel button."""
        button.label += " ✅"
        button.disabled = True
        for child in self.children:
            if type(child) == Button:
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id
