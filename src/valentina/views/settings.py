"""Views for configuring guild settings."""
from typing import cast

import discord
from discord.ext import pages
from discord.ui import Button
from loguru import logger

from valentina.constants import (
    CHANNEL_PERMISSIONS,
    ChannelPermission,
    EmbedColor,
    PermissionManageCampaign,
    PermissionsEditTrait,
    PermissionsEditXP,
)
from valentina.views import CancelButton


class SettingsButtons(discord.ui.View):
    """Add buttons to a view to set setting values.

    This class inherits from discord.ui.View and provides buttons to interactively
    set various settings in a Discord bot.

    Attributes:
        ctx: The Discord context object.
        options: A list of tuples containing the display label and the corresponding value.
        key: The key for the setting to be updated.
        current_value: The current value of the setting.
        setting_value: A dictionary containing the updated setting values.
    """

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        key: str,
        options: list[tuple[str, int]] | None = None,
        current_value: int | None = None,
    ):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.options = options
        self.key = key
        self.current_value = current_value
        self.setting_value: dict[str, int | None] = {}

        # Create buttons for each option
        for option in options:
            button: Button = Button(
                label=f"⚙️ {option[0]}" if self.current_value == option[1] else option[0],
                custom_id=str(option[1]),
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

    @discord.ui.button(label="🚫 Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")
    async def cancel_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Disable all buttons and stop the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        embed = interaction.message.embeds[0]
        embed.description = "## Cancelled\nNo settings were changed"
        embed.color = EmbedColor.WARNING.value  # type: ignore [method-assign, assignment]

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to the button press, update the database and the view."""
        # Disable the interaction and grab the setting name
        for child in self.children:
            if isinstance(child, Button):
                if str(self.current_value) == child.custom_id:
                    child.label = child.label[2:]

                if interaction.data.get("custom_id", None) == child.custom_id:
                    setting_name = child.label[2:]
                    child.label = f"✅ {child.label}"

            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Get the custom_id of the button that was pressed
        response = int(interaction.data.get("custom_id", None))  # type: ignore [call-overload]
        logger.warning(f"SettingsButtons.button_callback: {self.key=}:{response=}")

        # Update the database
        self.ctx.bot.guild_svc.update_or_add(ctx=self.ctx, updates={self.key: response})  # type: ignore [attr-defined]

        # Edit the original message
        embed = interaction.message.embeds[0]
        embed.description = (
            f"{embed.description}\n## 👍 Success\nSettings updated to `{setting_name}`"
        )
        embed.color = EmbedColor.SUCCESS.value  # type: ignore [method-assign, assignment]

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class SettingsChannelSelect(discord.ui.View):
    """Manage a UI view for channel selection in a guild.

    This class provides a UI view that allows users to select a channel from
    a dropdown. It then updates the specified setting in the database.

    Permissions are a tuple of (default, player, storyteller) permissions taken from constants.CHANNEL_PERMISSIONS.

    Attributes:
        ctx (discord.ApplicationContext): The application context for the command invocation.
        key (str): The database key for storing the channel ID.
        permissions (tuple[ChannelPermission, ChannelPermission, ChannelPermission]):
            A tuple containing permissions for various roles.
    """

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        key: str,
        permissions: tuple[ChannelPermission, ChannelPermission, ChannelPermission],
        channel_topic: str,
    ):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.key = key
        self.permissions = permissions
        self.channel_topic = channel_topic

    async def _update_guild_and_channel(
        self,
        enable: bool,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Update guild settings and channel permissions.

        Args:
            enable (bool): Whether to enable or disable the setting.
            channel (discord.TextChannel): The selected Discord text channel.
        """
        if enable and channel is not None:
            # Ensure the channel exists and has the right permissions
            await self.ctx.bot.guild_svc.channel_update_or_add(  # type: ignore [attr-defined]
                self.ctx,
                channel=channel,
                topic=self.channel_topic,
                permissions=self.permissions,
            )

            # Update the settings in the database
            self.ctx.bot.guild_svc.update_or_add(ctx=self.ctx, updates={self.key: channel.id})  # type: ignore [attr-defined]
            logger.debug(f"SettingsManager: {self.key=}:{channel.name=}")
        else:
            # Update the settings in the database
            self.ctx.bot.guild_svc.update_or_add(ctx=self.ctx, updates={self.key: None})  # type: ignore [attr-defined]
            logger.debug(f"SettingsManager: {self.key=}:None")

    @discord.ui.channel_select(
        placeholder="Select channel...",
        channel_types=[discord.ChannelType.text],
        min_values=1,
        max_values=1,
    )
    async def channel_select_dropdown(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ) -> None:
        """Respond to the selection, update the database and the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        selected_channel = cast(discord.TextChannel, select.values[0])

        await self._update_guild_and_channel(enable=True, channel=selected_channel)

        # Edit the original message
        embed = interaction.message.embeds[0]
        embed.description = (
            f"{embed.description}\n## 👍 Success\nSettings updated to {selected_channel.mention}"
        )
        embed.color = EmbedColor.SUCCESS.value  # type: ignore [method-assign, assignment]

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="⚠️ Disable", style=discord.ButtonStyle.primary, custom_id="disable")
    async def disable_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Disable all buttons and stop the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        await self._update_guild_and_channel(enable=False)

        # Edit the original message
        embed = interaction.message.embeds[0]
        embed.description = f"{embed.description}\n## 👍 Channel Disabled\n_No permissions were changed. No one who couldn't see the channel before can see it now._"
        embed.color = EmbedColor.SUCCESS.value  # type: ignore [method-assign, assignment]

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="🚫 Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")
    async def cancel_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Disable all buttons and stop the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Edit the original message
        embed = interaction.message.embeds[0]
        embed.description = "## Cancelled\nNo settings were changed"
        embed.color = EmbedColor.WARNING.value  # type: ignore [method-assign, assignment]

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class SettingsManager:
    """Manage guild settings."""

    def __init__(self, ctx: discord.ApplicationContext) -> None:
        self.ctx: discord.ApplicationContext = ctx

        self.current_settings = self.ctx.bot.guild_svc.fetch_guild_settings(self.ctx)  # type: ignore [attr-defined]
        self.page_group: list[pages.PageGroup] = [
            self._home_embed(),
            self._xp_permissions_embed(),
            self._trait_permissions_embed(),
            self._manage_campaigns_embed(),
            self._error_log(),
            self._audit_log(),
            self._storyteller_channel(),
        ]

    def _audit_log(self) -> pages.PageGroup:
        """Create a view for selecting the audit log channel."""
        description = [
            "# Interaction audit logging",
            "Valentina can log interactions to a channel of your choice. _IMPORTANT: The audit log channel will be hidden from everyone except for administrators and storytellers._",
            "### Instructions:",
            "- Select a channel from the dropdown below enable audit logging to that channel",
            "- Use the `Disable` button to disable audit logging",
            "- If you don't see the channel you want to use in the list, create it first and then re-run this command",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        view = SettingsChannelSelect(
            self.ctx,
            key="audit_log_channel_id",
            permissions=CHANNEL_PERMISSIONS["audit_log"],
            channel_topic="Valentina interaction audit reports",
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Audit Log",
            description="Select the channel to log interactions to",
            use_default_buttons=False,
        )

    def _error_log(self) -> pages.PageGroup:
        """Create a view for selecting the error log channel."""
        description = [
            "# Enable error logging",
            "Valentina can log errors to a channel of your choice. _IMPORTANT: The error log channel will be hidden from everyone except for administrators._",
            "### Instructions:",
            "- Select a channel from the dropdown below enable error logging to that channel",
            "- Use the `Disable` button to disable error logging",
            "- If you don't see the channel you want to use in the list, create it first and then re-run this command",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        view = SettingsChannelSelect(
            self.ctx,
            key="error_log_channel_id",
            permissions=CHANNEL_PERMISSIONS["error_log_channel"],
            channel_topic="Valentina error reports",
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Error Log Channel",
            description="Select the channel to log errors to",
            use_default_buttons=False,
        )

    def _home_embed(self) -> pages.PageGroup:
        """Create the home page group embed.

        Constructs an embed that serves as the home page for guild settings, displaying
        instructions and current settings.

        Returns:
            pages.PageGroup: A PageGroup object containing the embed and custom view for the home page.
        """
        settings_home_embed = discord.Embed(title="", color=EmbedColor.DEFAULT.value)

        # Gather information
        error_log_channel = self.ctx.bot.guild_svc.fetch_error_log_channel(self.ctx)  # type: ignore [attr-defined]
        audit_log_channel = self.ctx.bot.guild_svc.fetch_audit_log_channel(self.ctx)  # type: ignore [attr-defined]
        storyteller_channel = self.ctx.bot.guild_svc.fetch_storyteller_channel(self.ctx)  # type: ignore [attr-defined]

        settings_home_embed.description = "\n".join(
            [
                "# Manage Guild Settings",
                "### How this works",
                "1. Select the setting to manage from the select menu below",
                "2. Select the value to set from the buttons associated with each setting",
                "### Current Settings",
                "```yaml",
                "# Permissions",
                f"Grant experience   : {PermissionsEditXP(self.current_settings['permissions_edit_xp']).name.title()}",
                f"Update trait values: {PermissionsEditTrait(self.current_settings['permissions_edit_trait']).name.title()}",
                f"Manage campaign    : {PermissionManageCampaign(self.current_settings['permissions_manage_campaigns']).name.title()}",
                "",
                "# Channel Settings:",
                f"Storyteller channel: {storyteller_channel.name}"
                if storyteller_channel is not None
                else "Storyteller channel: Not set",
                "",
                "# Log to channels:",
                f"Log interactions: Enabled (#{audit_log_channel.name})"
                if audit_log_channel is not None
                else "Audit log: Disabled",
                f"Log errors: Enabled (#{error_log_channel.name})"
                if error_log_channel is not None
                else "Log errors: Disabled",
                "```",
            ]
        )

        view = CancelButton(self.ctx)
        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[settings_home_embed], custom_view=view),
            ],
            label="Home",
            description="Settings Homepage and Help",
            use_default_buttons=False,
        )

    def _manage_campaigns_embed(self) -> pages.PageGroup:
        """Create a view for setting who can manage campaigns.

        This method generates a Discord embed that provides options for setting permissions
        on who can manage campaigns. It also sets up buttons for the user to interact with.

        Returns:
            pages.PageGroup: A PageGroup object containing the embed and custom view for setting permissions.
        """
        description = [
            "# Settings for managing campaigns",
            "Controls who can perform the following actions on campaigns:",
            "- Create a new campaign",
            "- Delete a campaign",
            "- Set a campaign as active/inactive",
            "- Delete NPCs, notes, and chapters from a campaign",
            "### Options:",
            "1. **Unrestricted** - Any user can manage campaigns",
            "2. **Storyteller only** - Only a Storyteller can manage campaigns",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        # Build options for the buttons and the view
        options = [
            (f"{x.value + 1}. {x.name.title().replace('_', ' ')}", x.value)
            for x in PermissionManageCampaign
        ]
        view = SettingsButtons(
            self.ctx,
            key="permissions_manage_campaigns",
            options=options,
            current_value=int(self.current_settings["permissions_manage_campaigns"]),
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Manage Campaigns",
            description="Who can manage campaigns",
            use_default_buttons=False,
        )

    def _storyteller_channel(self) -> pages.PageGroup:
        """Create a view for selecting the storyteller channel."""
        description = [
            "# Storyteller channel",
            "Valentina can set up a channel for storytellers to use to communicate with each other and run commands in private. _IMPORTANT: The storyteller channel will be hidden from everyone except for administrators and storytellers._",
            "### Instructions:",
            "- Select a channel from the dropdown to select a storyteller channel and set it's permissions",
            "- If you don't see the channel you want to use in the list, create it first and then re-run this command",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        view = SettingsChannelSelect(
            self.ctx,
            key="storyteller_channel_id",
            permissions=CHANNEL_PERMISSIONS["storyteller_channel"],
            channel_topic="Private channel for storytellers",
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Storyteller Channel",
            description="Select the channel to use for storytellers",
            use_default_buttons=False,
        )

    def _trait_permissions_embed(self) -> pages.PageGroup:
        """Create a view for setting Trait Update permissions.

        This method generates a Discord embed that provides options for setting permissions
        on who can update trait values on characters. It also sets up buttons for
        the user to interact with.

        Returns:
            pages.PageGroup: A PageGroup object containing the embed and custom view for setting permissions.
        """
        description = [
            "# Settings for updating Trait Values",
            "Control who can update the values of character traits without spending experience.",
            "### Options:",
            "1. **Unrestricted** - Any user can update the value of any character's traits",
            "2. **Owner Only** - The owner of a character can update the value of that character's traits",
            "3. **Within 24 hours** - The owner of a character can update the value of that character's traits within 24 hours of creation",
            "3. **Storyteller only** - Only a Storyteller can manually update the value of a character's traits",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        # Build options for the buttons and the view
        options = [
            (f"{x.value + 1}. {x.name.title().replace('_', ' ')}", x.value)
            for x in PermissionsEditTrait
        ]
        view = SettingsButtons(
            self.ctx,
            key="permissions_edit_trait",
            options=options,
            current_value=int(self.current_settings["permissions_edit_trait"]),
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Edit Trait Values",
            description="Who can edit trait values without spending experience",
            use_default_buttons=False,
        )

    def _xp_permissions_embed(self) -> pages.PageGroup:
        """Create a view for setting XP permissions.

        This method generates a Discord embed that provides options for setting permissions
        on who can grant experience points (XP) to characters. It also sets up buttons for
        the user to interact with.

        Returns:
            pages.PageGroup: A PageGroup object containing the embed and custom view for setting permissions.
        """
        description = [
            "# Settings for editing XP",
            "Control who can grant experience to a character",
            "### Options:",
            "1. **Unrestricted** - Any user can grant experience to any character",
            "2. **Owner Only** - The owner of a character can grant experience to that character",
            "3. **Within 24 hours** - The owner of a character can grant experience to that character within 24 hours of creation",
            "3. **Storyteller only** - Only a Storyteller can grant experience to players' characters",
        ]

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )

        # Build options for the buttons and the view
        options = [
            (f"{x.value + 1}. {x.name.title().replace('_', ' ')}", x.value)
            for x in PermissionsEditXP
        ]
        view = SettingsButtons(
            self.ctx,
            key="permissions_edit_xp",
            options=options,
            current_value=int(self.current_settings["permissions_edit_xp"]),
        )

        return pages.PageGroup(
            pages=[
                pages.Page(embeds=[embed], custom_view=view),
            ],
            label="Grant Experience",
            description="Who can grant experience to a character",
            use_default_buttons=False,
        )

    def display_settings_manager(self) -> pages.Paginator:
        """Display the settings manager.

        Display the settings manager as a paginator to navigate through different settings.

        Returns:
            pages.Paginator: The paginator object containing all the settings pages.
        """
        return pages.Paginator(
            pages=self.page_group,
            show_menu=True,
            menu_placeholder="Navigate To Setting",
            show_disabled=False,
            show_indicator=False,
            use_default_buttons=False,
            custom_buttons=[],
        )
