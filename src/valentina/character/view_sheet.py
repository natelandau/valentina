"""View a character sheet."""
from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina import char_svc
from valentina.models.database import Character

MAX_DOT_DISPLAY = 6


def __build_trait_display(
    char_traits: dict[str, Any],
    categories_list: list[str],
    exclude_from_list: bool = False,
    show_zeros: bool = True,
) -> list[tuple[str, str]]:
    """Builds the name and value for an embed field representing a category of traits.

    Args:
        char_traits (dict[str, Any]): A dictionary of character traits.
        categories_list (list[str]): A list of categories to include in the embed field.
        exclude_from_list (bool, optional): If True, the categories list is treated as a list of categories to exclude. Defaults to False.
        show_zeros (bool, optional): If True, traits with a value of 0 are included in the embed field. Defaults to True.
    """
    embed_values = []
    for category, traits in char_traits.items():
        if exclude_from_list and category.lower() in [x.lower() for x in categories_list]:
            continue
        if not exclude_from_list and category.lower() not in [x.lower() for x in categories_list]:
            continue

        formatted = []
        for trait, value, max_value, dots in traits:
            if not show_zeros and value == 0:
                continue
            if max_value > MAX_DOT_DISPLAY:
                formatted.append(f"`{trait:13}: {value}/{max_value}`")
            else:
                formatted.append(f"`{trait:13}: {dots}`")

        embed_values.append((category, "\n".join(formatted)))

    return embed_values


def __embed1(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User | None = None,
) -> discord.Embed:
    """Builds the first embed of a character sheet. This embed contains the character's name, class, experience, cool points, and attributes and abilities."""
    modified = arrow.get(character.modified).humanize()
    char_traits = char_svc.fetch_all_character_trait_values(ctx, character)

    embed = discord.Embed(title=f"{character.name}", description="", color=0x7777FF)
    embed.set_footer(text=f"{character.name} last updated {modified}")

    embed.add_field(name="Class", value=character.class_name, inline=True)

    if character.class_name.lower() == "vampire" and character.clan:
        embed.add_field(name="Clan", value=character.clan.name, inline=True)

    embed.add_field(
        name="Claimed By", value=f"{claimed_by.mention}" if claimed_by else "-", inline=True
    )

    embed.add_field(name="\u200b", value="**EXPERIENCE**", inline=False)
    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(name="Cool Points", value=f"`{character.cool_points}`", inline=True)

    embed.add_field(name="\u200b", value="**ATTRIBUTES**", inline=False)
    for category, traits in __build_trait_display(char_traits, ["physical", "social", "mental"]):
        embed.add_field(name=category, value=traits, inline=True)

    embed.add_field(name="\u200b", value="**ABILITIES**", inline=False)
    for category, traits in __build_trait_display(char_traits, ["talents", "skills", "knowledges"]):
        embed.add_field(name=category, value=traits, inline=True)

    for category, traits in __build_trait_display(
        char_traits,
        [
            "physical",
            "social",
            "mental",
            "talents",
            "skills",
            "knowledges",
            "disciplines",
            "spheres",
        ],
        exclude_from_list=True,
    ):
        embed.add_field(name=category, value=traits, inline=True)

    # Show class specific traits.
    # Werewolf/hunter traits aren't here b/c they are not a large list and should be shown with the rest of the traits with zeros included.
    class_list = []
    match character.class_name.lower():
        case "vampire":
            class_list = ["disciplines"]
        case "mage":
            class_list = ["spheres"]

    for category, traits in __build_trait_display(char_traits, class_list, show_zeros=False):
        embed.add_field(name=category, value=traits, inline=True)

    return embed


def __embed2(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User | None = None,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    custom_sections = char_svc.fetch_char_custom_sections(ctx, character)
    # Return None if there is no bio or custom sections
    if not character.bio and len(custom_sections) == 0:
        return None

    modified = arrow.get(character.modified).humanize()
    embed = discord.Embed(title=f"{character.name} - Page 2", description="", color=0x7777FF)
    embed.set_footer(text=f"{character.name} last updated {modified}")

    embed.add_field(name="Class", value=character.class_name, inline=True)

    if character.class_name.lower() == "vampire" and character.clan:
        embed.add_field(name="Clan", value=character.clan.name, inline=True)

    embed.add_field(
        name="Claimed By", value=f"{claimed_by.mention}" if claimed_by else "-", inline=True
    )

    if character.bio:
        embed.add_field(name=f"**About {character.name}**", value=character.bio, inline=False)

    if len(custom_sections) > 0:
        embed.add_field(name="\u200b", value="**CUSTOM SECTIONS**", inline=False)
        for section in custom_sections:
            embed.add_field(
                name=f"__**{section.title.upper()}**__", value=section.description, inline=True
            )

    return embed


async def show_sheet(
    ctx: discord.ApplicationContext,
    character: Character,
    claimed_by: discord.User,
    ephemeral: Any = False,
) -> Any:
    """Show a character sheet."""
    embed1 = __embed1(ctx, character, claimed_by)
    embed2 = __embed2(ctx, character, claimed_by)

    if embed2 is None:
        await ctx.respond(embed=embed1, ephemeral=ephemeral)
        return

    paginator = pages.Paginator(pages=[embed1, embed2])  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)
