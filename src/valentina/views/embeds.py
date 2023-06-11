"""Prebuilt embeds for Valentina."""

import discord

from valentina.models.constants import EmbedColor


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
) -> None:
    """Display an error in a nice embed.

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

    await ctx.respond(embed=embed, ephemeral=ephemeral)
