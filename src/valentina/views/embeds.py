"""Prebuilt embeds for Valentina."""

from typing import Any

import discord

from valentina.models.constants import EmbedColor


class ConfirmCancelView(discord.ui.View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User):
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
        return interaction.user.id == self.author.id


async def present_embed(
    ctx: discord.ApplicationContext,
    title: str = "",
    description: str = "",
    footer: str = None,
    level: str = "INFO",
    ephemeral: bool = False,
    fields: list[tuple[str, str]] = [],
    inline_fields: bool = False,
    thumbnail: str = None,
    author: str = None,
    author_avatar: str = None,
    view: Any = None,
) -> None:
    """Display a nice embed.

    Args:
        ctx: The Discord context for sending the response.
        title: The title of the embed.
        description: The description of the embed.
        ephemeral: Whether the embed should be ephemeral.
        level: The level of the embed. Effects the color.(INFO, ERROR, WARNING, SUCCESS)
        fields: list(tuple(str,  str)): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        footer (str): Footer text to display.
        inline_fields (bool): Whether the fields should be inline (Default: False).
        thumbnail (str): URL of the thumbnail to display.
        author (str): Name of the author to display.
        author_avatar (str): URL of the author's avatar to display.
        view (discord.ui.View): The view to add to the embed.
    """
    color = EmbedColor[level.upper()].value

    embed = discord.Embed(title=title, colour=color)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

    embed.description = description

    if author and thumbnail:
        embed.set_author(name=author, icon_url=author_avatar)
    elif author:
        embed.set_author(name=author)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    for field in fields:
        name, value = field
        embed.add_field(name=name, value=value, inline=inline_fields)

    if footer:
        embed.set_footer(text=footer)

    if view:
        await ctx.respond(embed=embed, ephemeral=ephemeral, view=view)
    else:
        await ctx.respond(embed=embed, ephemeral=ephemeral)
