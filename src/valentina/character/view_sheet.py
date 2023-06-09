"""View a character sheet."""
from typing import Any

import arrow
import discord

from valentina.models.constants import (
    GROUPED_TRAITS,
    HUNTER_TRAITS,
    MAGE_SPHERES,
    MAGE_TRAITS,
    UNIVERSAL_TRAITS,
    VAMPIRE_DISCIPLINES,
    VIRTUES,
    WEREWOLF_TRAITS,
)
from valentina.models.database import Character
from valentina.utils.helpers import format_traits


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

    if character.bio:
        embed.add_field(name="bio", value=character.bio, inline=False)

    embed.add_field(name="Class", value=character.class_name, inline=True)
    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(name="Cool Points", value=f"`{character.cool_points}`", inline=True)

    for group, subgroups in GROUPED_TRAITS.items():
        embed.add_field(name="\u200b", value=f"**{group}**", inline=False)
        for subgroup, traits in subgroups.items():
            embed.add_field(name=subgroup, value=format_traits(character, traits), inline=True)

    embed.add_field(name="Virtues", value=format_traits(character, VIRTUES), inline=True)
    embed.add_field(name="Universal", value=format_traits(character, UNIVERSAL_TRAITS), inline=True)

    match character.class_name.lower():
        case "mage":
            embed.add_field(name="Mage", value=format_traits(character, MAGE_TRAITS), inline=True)
            embed.add_field(
                name="Spheres", value=format_traits(character, MAGE_SPHERES, False), inline=True
            )
        case "vampire":
            embed.add_field(
                name="Disciplines",
                value=format_traits(character, VAMPIRE_DISCIPLINES, False),
                inline=True,
            )

        case "werewolf":
            embed.add_field(
                name="Werewolf", value=format_traits(character, WEREWOLF_TRAITS), inline=True
            )
        case "hunter":
            embed.add_field(
                name="Hunter", value=format_traits(character, HUNTER_TRAITS), inline=True
            )

    msg_contents = {"embed": embed}
    msg_contents["ephemeral"] = ephemeral
    return await ctx.respond(**msg_contents)
