"""View a character sheet."""
from typing import Any

import arrow
import discord

from valentina import char_svc
from valentina.models.database import Character


async def show_sheet(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User,
    ephemeral: Any = False,
) -> Any:
    """Show a character sheet."""
    title = character.name
    modified = arrow.get(character.modified).humanize()
    embed = discord.Embed(title=title, description="", color=0x7777FF)

    embed.set_footer(text=f"Last updated {modified}")

    if character.bio:
        embed.add_field(name="Bio", value=character.bio, inline=False)

    if claimed_by:
        embed.description = f"Claimed by {claimed_by.mention}"

    embed.add_field(name="Class", value=character.class_name, inline=True)
    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(name="Cool Points", value=f"`{character.cool_points}`", inline=True)

    char_traits = char_svc.fetch_all_character_trait_values(character)

    for category, traits in char_traits.items():
        formatted_traits = []
        for trait, _value, dots in traits:
            formatted_traits.append(f"`{trait:13}: {dots}`")

        embed.add_field(name=category, value="\n".join(formatted_traits), inline=True)

    msg_contents = {"embed": embed}
    msg_contents["ephemeral"] = ephemeral
    return await ctx.respond(**msg_contents)
