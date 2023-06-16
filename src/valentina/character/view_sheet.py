"""View a character sheet."""
from typing import Any

import arrow
import discord

from valentina.models.constants import GROUPED_TRAITS
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

    embed.add_field(name="\u200b", value="**ATTRIBUTES**", inline=False)
    embed.add_field(
        name="Physical", value=format_traits(character, GROUPED_TRAITS["ATTRIBUTES"]["Physical"])
    )
    embed.add_field(
        name="Social", value=format_traits(character, GROUPED_TRAITS["ATTRIBUTES"]["Social"])
    )
    embed.add_field(
        name="Mental", value=format_traits(character, GROUPED_TRAITS["ATTRIBUTES"]["Mental"])
    )

    embed.add_field(name="\u200b", value="**ABILITIES**", inline=False)
    embed.add_field(
        name="Talents", value=format_traits(character, GROUPED_TRAITS["ABILITIES"]["Talents"])
    )
    embed.add_field(
        name="Skills", value=format_traits(character, GROUPED_TRAITS["ABILITIES"]["Skills"])
    )
    embed.add_field(
        name="Knowledges", value=format_traits(character, GROUPED_TRAITS["ABILITIES"]["Knowledges"])
    )

    embed.add_field(
        name="Virtues", value=format_traits(character, GROUPED_TRAITS["COMMON"]["Virtues"])
    )
    embed.add_field(
        name="Universal", value=format_traits(character, GROUPED_TRAITS["COMMON"]["Universal"])
    )
    match character.class_name.lower():
        case "mage":
            mage_traits = GROUPED_TRAITS["MAGE"]["Universal"] + GROUPED_TRAITS["MAGE"]["Spheres"]
            embed.add_field(name="Mage", value=format_traits(character, mage_traits, False))
        case "vampire":
            vampire_traits = (
                GROUPED_TRAITS["VAMPIRE"]["Universal"] + GROUPED_TRAITS["VAMPIRE"]["Disciplines"]
            )
            embed.add_field(name="Vampire", value=format_traits(character, vampire_traits, False))
        case "werewolf":
            embed.add_field(
                name="Werewolf",
                value=format_traits(character, GROUPED_TRAITS["WEREWOLF"]["Universal"], False),
            )
        case "hunter":
            embed.add_field(
                name="Hunter",
                value=format_traits(character, GROUPED_TRAITS["HUNTER"]["Universal"], False),
            )

    msg_contents = {"embed": embed}
    msg_contents["ephemeral"] = ephemeral
    return await ctx.respond(**msg_contents)
