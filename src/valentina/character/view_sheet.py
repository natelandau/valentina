"""View a character sheet."""
from typing import Any

import arrow
import discord

from valentina.models.database import Character


async def show_sheet(
    ctx: discord.ApplicationContext, character: Character, ephemeral: Any = False
) -> Any:
    """Show a character sheet."""
    player = ctx.user
    title = character.name
    modified = arrow.get(character.modified).humanize()
    embed = discord.Embed(title=title, description="", color=0x7777FF)

    embed.set_author(name="")  # appears above title
    embed.set_footer(text=f"Player {player}\nLast updated: {modified}")

    # Todo: Query character for fields
    if character.bio:
        embed.add_field(name="bio", value=character.bio, inline=False)

    embed.add_field(name="Class", value=character.class_name, inline=False)
    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(name="Cool Points", value=f"`{character.cool_points}`", inline=True)

    msg_contents = {"embed": embed}
    msg_contents["ephemeral"] = ephemeral
    return await ctx.respond(**msg_contents)
