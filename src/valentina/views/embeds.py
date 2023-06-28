"""Prebuilt embeds for Valentina."""

from datetime import datetime
from typing import Any

import discord

from valentina import guild_svc
from valentina.models.constants import EmbedColor


async def present_embed(  # noqa: C901
    ctx: discord.ApplicationContext,
    title: str = "",
    description: str = "",
    log: str | bool = False,
    footer: str | None = None,
    level: str = "INFO",
    ephemeral: bool = False,
    fields: list[tuple[str, str]] = [],
    inline_fields: bool = False,
    thumbnail: str | None = None,
    author: str | None = None,
    author_avatar: str | None = None,
    show_author: bool = False,
    timestamp: bool = False,
    view: Any = None,
    delete_after: float | None = None,
) -> None:
    """Display a nice embed.

    Args:
        ctx: The Discord context for sending the response.
        title: The title of the embed.
        description: The description of the embed.
        ephemeral: Whether the embed should be ephemeral.
        level: The level of the embed. Effects the color.(INFO, ERROR, WARNING, SUCCESS)
        log(str | bool): Whether to log the embed to the guild log channel. If a string is sent, it will be used as the log message.
        fields: list(tuple(str,  str)): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        delete_after (optional, float): Number of seconds to wait before deleting the message.
        footer (str): Footer text to display.
        inline_fields (bool): Whether the fields should be inline (Default: False).
        thumbnail (str): URL of the thumbnail to display.
        show_author (bool): Whether to show the author of the embed.
        author (str): Name of the author to display.
        author_avatar (str): URL of the author's avatar to display.
        timestamp (bool): Whether to show the timestamp.
        view (discord.ui.View): The view to add to the embed.
    """
    color = EmbedColor[level.upper()].value

    embed = discord.Embed(title=title, colour=color)
    if show_author:
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

    embed.description = description

    if author and thumbnail:
        embed.set_author(name=author, icon_url=author_avatar)
    elif author:
        embed.set_author(name=author)
    elif thumbnail:
        embed.set_thumbnail(url=thumbnail)

    for field in fields:
        name, value = field
        embed.add_field(name=name, value=value, inline=inline_fields)

    if footer:
        embed.set_footer(text=footer)

    if timestamp:
        embed.timestamp = datetime.now()

    if log:
        await log_to_channel(ctx, log, embed)

    if view and delete_after:
        await ctx.respond(embed=embed, ephemeral=ephemeral, view=view, delete_after=delete_after)
    elif view:
        await ctx.respond(embed=embed, ephemeral=ephemeral, view=view)
    elif delete_after:
        await ctx.respond(embed=embed, ephemeral=ephemeral, delete_after=delete_after)
    else:
        await ctx.respond(embed=embed, ephemeral=ephemeral)


async def log_to_channel(
    ctx: discord.ApplicationContext,
    log: str | bool,
    embed: discord.Embed | None = None,
) -> None:
    """Log an event to the guild log channel."""
    if isinstance(log, str):
        await guild_svc.send_log(ctx, log)
    else:
        log_embed = embed.copy()
        log_embed.timestamp = datetime.now()
        log_embed.set_footer(
            text=f"Command invoked by {ctx.author.display_name} in #{ctx.channel.name}"
        )
        await guild_svc.send_log(ctx, log_embed)
