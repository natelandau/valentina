"""View a character sheet."""
from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina import char_svc
from valentina.models.database import Character

MAX_DOT_DISPLAY = 6


def __build_trait_display(trait: str, value: int, max_value: int, dots: str) -> str:
    """Builds a display string for a trait."""
    if max_value > MAX_DOT_DISPLAY:
        return f"`{trait:13}: {value}/{max_value}`"

    return f"`{trait:13}: {dots}`"


def __embed1(  # noqa: C901
    ctx: discord.ApplicationContext,
    character: Character,
) -> discord.Embed:
    """Builds the first embed of a character sheet. This embed contains the character's name, class, experience, cool points, and attributes and abilities."""
    modified = arrow.get(character.modified).humanize()
    char_traits = char_svc.fetch_all_character_trait_values(ctx, character)

    embed = discord.Embed(title=f"{character.name}", description="", color=0x7777FF)
    embed.add_field(name="Class", value=character.class_name, inline=True)

    if character.class_name.lower() == "vampire" and character.clan:
        embed.add_field(name="Clan", value=character.clan.name, inline=True)

    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(name="Cool Points", value=f"`{character.cool_points}`", inline=True)
    embed.set_footer(text=f"{character.name} last updated {modified}")
    embed.add_field(name="\u200b", value="**ATTRIBUTES**", inline=False)

    for category, traits in char_traits.items():
        if category.lower() in ["physical", "social", "mental"]:
            formatted_traits = []
            for trait, value, max_value, dots in traits:
                formatted_traits.append(__build_trait_display(trait, value, max_value, dots))

            embed.add_field(name=category, value="\n".join(formatted_traits), inline=True)

    embed.add_field(name="\u200b", value="**ABILITIES**", inline=False)
    for category, traits in char_traits.items():
        if category.lower() in ["talents", "skills", "knowledges"]:
            formatted_traits = []
            for trait, value, max_value, dots in traits:
                formatted_traits.append(__build_trait_display(trait, value, max_value, dots))

            embed.add_field(name=category, value="\n".join(formatted_traits), inline=True)

    for category, traits in char_traits.items():
        if category.lower() not in [
            "physical",
            "social",
            "mental",
            "talents",
            "skills",
            "knowledges",
        ]:
            formatted_traits = []
            for trait, value, max_value, dots in traits:
                formatted_traits.append(__build_trait_display(trait, value, max_value, dots))

            embed.add_field(name=category, value="\n".join(formatted_traits), inline=True)

    return embed


def __embed2(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    custom_sections = char_svc.fetch_char_custom_sections(ctx, character)
    # Return None if there is no bio or custom sections
    if not character.bio and len(custom_sections) == 0:
        return None

    modified = arrow.get(character.modified).humanize()
    embed = discord.Embed(title=f"{character.name} - Page 2", description="", color=0x7777FF)
    embed.set_footer(text=f"{character.name} last updated {modified}")

    if claimed_by:
        embed.description = f"Claimed by {claimed_by.mention}"

    if character.bio:
        embed.add_field(name="Bio", value=character.bio, inline=False)

    if len(custom_sections) > 0:
        embed.add_field(name="\u200b", value="**CUSTOM SECTIONS**", inline=False)
        for section in custom_sections:
            embed.add_field(name=section.title, value=section.description, inline=True)

    return embed


async def show_sheet(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User,
    ephemeral: Any = False,
) -> Any:
    """Show a character sheet."""
    embed1 = __embed1(ctx, character)
    embed2 = __embed2(ctx, character, claimed_by)

    if embed2 is None:
        await ctx.respond(embed=embed1, ephemeral=ephemeral)
        return

    paginator = pages.Paginator(pages=[embed1, embed2])  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)
