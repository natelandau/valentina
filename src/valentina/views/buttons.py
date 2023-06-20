"""Buttons and views for Valentina."""
import discord


class ConfirmCancelButtons(discord.ui.View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User | discord.Member | None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="😎")
    async def submit_callback(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        """Callback for the confirm button."""
        button.label += " ✅"
        await interaction.response.edit_message(view=self)
        self.confirmed = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="🤬")
    async def cancel_callback(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        """Callback for the cancel button."""
        button.label += " ✅"
        await interaction.response.edit_message(view=self)
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id
