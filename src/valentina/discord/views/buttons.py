"""Buttons and views for Valentina."""

import discord
from discord.ui import Button

from valentina.constants import MAX_BUTTONS_PER_ROW, EmojiDict


class IntegerButtons(discord.ui.View):
    """Add integer buttons to a view."""

    def __init__(self, numbers: list[int], author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.numbers = numbers
        self.selection: int = None
        self.cancelled = False

        for i in sorted(numbers):
            button: Button = Button(
                label=str(i),
                custom_id=str(i),
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

        rows = len(numbers) // MAX_BUTTONS_PER_ROW

        cancel_button: Button = Button(
            label=f"{EmojiDict.CANCEL} Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel",
            row=rows + 1 if rows < 5 else 5,  # noqa: PLR2004
        )
        cancel_button.callback = self.cancel_callback  # type: ignore [method-assign]
        self.add_item(cancel_button)

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a character."""
        await interaction.response.defer()
        # Disable the interaction and grab the setting name
        for child in self.children:
            if (
                isinstance(child, Button)
                and interaction.data.get("custom_id", None) == child.custom_id
            ):
                child.label = f"{EmojiDict.YES} {child.label}"

            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Return the selected character based on the custom_id of the button that was pressed

        self.selection = int(interaction.data.get("custom_id", None))  # type: ignore[call-overload]
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.cancelled = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True

        if self.author.guild_permissions.administrator:  # type: ignore [union-attr]
            return True

        return interaction.user.id == self.author.id


class ReRollButton(discord.ui.View):
    """Add a re-roll button to a view.  When desperation botch is True, choices to enter Overreach or Despair will replace the re-roll button."""

    def __init__(
        self,
        author: discord.User | discord.Member | None = None,
        desperation_pool: int = 0,
        desperation_botch: bool = False,
    ):
        super().__init__(timeout=60)

        self.author = author
        self.desperation_pool = desperation_pool
        self.desperation_botch = desperation_botch
        self.reroll: bool = None
        self.overreach: bool = False
        self.despair: bool = False

        if self.desperation_pool == 0:  # Add reroll and done buttons if not a desperation roll
            reroll_button: Button = Button(
                label="Re-Roll",
                custom_id="reroll",
                style=discord.ButtonStyle.success,
            )
            reroll_button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(reroll_button)

            done_button: Button = Button(
                label="Done",
                custom_id="done",
                style=discord.ButtonStyle.secondary,
            )
            done_button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(done_button)
        elif desperation_botch:
            overreach_button: Button = Button(
                label=f"{EmojiDict.OVERREACH} Succeed and increase danger!",
                custom_id="overreach",
                style=discord.ButtonStyle.success,
            )
            overreach_button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(overreach_button)

            despair_button: Button = Button(
                label=f"{EmojiDict.DESPAIR} Fail and enter Despair!",
                custom_id="despair",
                style=discord.ButtonStyle.success,
            )
            despair_button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(despair_button)

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to the button press and update the view."""
        # Get the custom_id of the button that was pressed
        response = interaction.data.get("custom_id", None)

        # Disable the interaction and grab the setting name
        for child in self.children:
            if isinstance(child, Button) and response == child.custom_id:
                child.label = f"{EmojiDict.YES} {child.label}"

        self._disable_all()
        await interaction.response.edit_message(view=None)  # view=None remove all buttons

        if response == "done":
            self.reroll = False
        if response == "reroll":
            self.reroll = True
        if response == "overreach":
            self.reroll = False
            self.overreach = True
        if response == "despair":
            self.reroll = False
            self.despair = True

        self.stop()

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True

        if self.author.guild_permissions.administrator:  # type: ignore [union-attr]
            return True

        return interaction.user.id == self.author.id


class ConfirmCancelButtons(discord.ui.View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label += f" {EmojiDict.YES}"
        self._disable_all()
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    @discord.ui.button(
        label=f"{EmojiDict.CANCEL} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
    )
    async def cancel_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the cancel button."""
        button.label += f" {EmojiDict.YES}"
        self._disable_all()
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

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{EmojiDict.CANCEL} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
    )
    async def cancel_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the cancel button."""
        self._disable_all()
        await interaction.response.edit_message(view=self)  # view=None remove all buttons
        self.confirmed = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id
