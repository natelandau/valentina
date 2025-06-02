"""Prebuilt embeds for Valentina."""

from datetime import UTC, datetime
from typing import Any

import discord
from discord.ext import commands, pages

from valentina.constants import ABS_MAX_EMBED_CHARACTERS, PREF_MAX_EMBED_CHARACTERS, EmbedColor
from valentina.discord.bot import ValentinaContext


async def auto_paginate(  # noqa: PLR0913
    ctx: discord.ApplicationContext,
    title: str,
    text: str,
    url: str | None = None,
    max_chars: int = PREF_MAX_EMBED_CHARACTERS,
    color: EmbedColor = EmbedColor.INFO,
    footer: str | None = None,
    show_thumbnail: bool = False,
    hidden: bool = False,
) -> None:
    """Display text in Discord, paginating if necessary.

    Be aware, this command may split apart multi-line code blocks.

    Embeds can take 4000 characters in the description field, but we default to ~1300 for the sake of not scrolling forever.

    Args:
        ctx (discord.ApplicationContext): The context of the interaction.
        title (str): The title of the paginator.
        text (str): The text to paginate.
        url (str, optional): The URL to link to. Defaults to None.
        max_chars (int, optional): The maximum number of characters per page. Defaults to 1300.
        show_thumbnail (bool, optional): Whether to show the bot's thumbnail. Defaults to False.
        color (EmbedColor, optional): The color of the embed. Defaults to EmbedColor.INFO.
        footer (str, optional): The footer text. Defaults to None.
        hidden (bool, optional): Whether to hide the message from other users. Defaults to False.
    """
    max_chars = min(max_chars, ABS_MAX_EMBED_CHARACTERS)

    p = commands.Paginator(prefix="", suffix="", max_size=max_chars)
    for line in text.splitlines():
        p.add_line(line)

    embeds = [
        discord.Embed(title=title, description=page, url=url, color=color.value) for page in p.pages
    ]

    if show_thumbnail:
        for embed in embeds:
            embed.set_thumbnail(url=ctx.bot.user.display_avatar)

    if footer:
        for embed in embeds:
            embed.set_footer(text=footer)

    show_buttons = len(embeds) > 1
    paginator = pages.Paginator(
        embeds,  # type: ignore [arg-type]
        author_check=False,
        show_disabled=show_buttons,
        show_indicator=show_buttons,
    )
    await paginator.respond(ctx.interaction, ephemeral=hidden)


def user_error_embed(ctx: ValentinaContext, msg: str, error: str) -> discord.Embed:
    """Create an embed for user errors.

    Args:
        ctx (ValentinaContext): The context of the command.
        msg (str): The message to display in the embed.
        error (str): The error to display in the embed.

    Returns:
        discord.Embed: The embed to send.
    """
    description = "" if error == msg else error

    embed = discord.Embed(title=msg, description=description, color=EmbedColor.ERROR.value)
    embed.timestamp = datetime.now(UTC)

    if hasattr(ctx, "command"):
        embed.set_footer(text=f"Command: /{ctx.command}")

    return embed


async def present_embed(  # noqa: PLR0913
    ctx: ValentinaContext,
    title: str = "",
    description: str = "",
    footer: str | None = None,
    level: str = "INFO",
    ephemeral: bool = False,
    fields: list[tuple[str, str]] = [],
    image: str | None = None,
    inline_fields: bool = False,
    thumbnail: str | None = None,
    author: str | None = None,
    author_avatar: str | None = None,
    show_author: bool = False,
    timestamp: bool = False,
    view: Any = None,
    delete_after: float = 120.0,  # 2 minutes by default
) -> discord.Interaction:
    """Display a nice embed.

    Args:
        ctx: The Discord context for sending the response.
        title: The title of the embed.
        description: The description of the embed.
        ephemeral: Whether the embed should be ephemeral.
        level: The level of the embed. Effects the color.(INFO, ERROR, WARNING, SUCCESS)
        fields: list(tuple(str,  str)): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        delete_after (optional, float): Number of seconds to wait before deleting the message.
        footer (str): Footer text to display.
        image (str): URL of the image to display.
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

    if author and author_avatar:
        embed.set_author(name=author, icon_url=author_avatar)
    elif author:
        embed.set_author(name=author)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    for name, value in fields:
        embed.add_field(name=name, value=value, inline=inline_fields)

    if image:
        embed.set_image(url=image)

    if footer:
        embed.set_footer(text=footer)

    if timestamp:
        embed.timestamp = datetime.now(UTC)

    respond_kwargs = {
        "embed": embed,
        "ephemeral": ephemeral,
        "delete_after": delete_after,
    }
    if view:
        respond_kwargs["view"] = view
    return await ctx.respond(**respond_kwargs)  # type: ignore [return-value]
