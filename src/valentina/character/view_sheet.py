"""View a character sheet."""
from typing import Any

import arrow
import discord

from valentina.models.constants import COMMON_TRAITS
from valentina.models.database import Character
from valentina.utils.helpers import format_traits


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

    embed.add_field(name="\u200b", value="**ATTRIBUTES**", inline=False)
    embed.add_field(name="Physical", value=format_traits(character, COMMON_TRAITS["Physical"]))
    embed.add_field(name="Social", value=format_traits(character, COMMON_TRAITS["Social"]))
    embed.add_field(name="Mental", value=format_traits(character, COMMON_TRAITS["Mental"]))

    embed.add_field(name="\u200b", value="**ABILITIES**", inline=False)
    embed.add_field(name="Talents", value=format_traits(character, COMMON_TRAITS["Talents"]))
    embed.add_field(name="Skills", value=format_traits(character, COMMON_TRAITS["Skills"]))
    embed.add_field(name="Knowledges", value=format_traits(character, COMMON_TRAITS["Knowledges"]))

    embed.add_field(name="Virtues", value=format_traits(character, COMMON_TRAITS["Virtues"]))
    embed.add_field(name="Universal", value=format_traits(character, COMMON_TRAITS["Universal"]))

    match character.class_name.lower():
        case "mage":
            mage_traits = COMMON_TRAITS["COMMON_TRAITS"] + COMMON_TRAITS["Spheres"]
            embed.add_field(name="Mage", value=format_traits(character, mage_traits, False))
        case "vampire":
            vampire_traits = COMMON_TRAITS["Vampire"] + COMMON_TRAITS["Disciplines"]
            embed.add_field(name="Vampire", value=format_traits(character, vampire_traits, False))
        case "werewolf":
            werewolf_traits = COMMON_TRAITS["Werewolf"] + COMMON_TRAITS["Renown"]
            embed.add_field(
                name="Werewolf",
                value=format_traits(character, werewolf_traits, False),
            )
        case "hunter":
            embed.add_field(
                name="Hunter",
                value=format_traits(character, COMMON_TRAITS["Hunter"], False),
            )

    msg_contents = {"embed": embed}
    msg_contents["ephemeral"] = ephemeral
    return await ctx.respond(**msg_contents)
