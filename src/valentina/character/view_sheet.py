"""View a character sheet."""
from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina.models.database import Character

MAX_DOT_DISPLAY = 6


def __build_trait_display(
    char_traits: dict[str, Any],
    categories_list: list[str],
    exclude_from_list: bool = False,
    show_zeros: bool = True,
    sort_items: bool = False,
) -> list[tuple[str, str]]:
    """Builds the name and value for an embed field representing a category of traits.

    Args:
        char_traits (dict[str, Any]): A dictionary of character traits.
        categories_list (list[str]): A list of categories to include in the embed field.
        exclude_from_list (bool, optional): If True, the categories list is treated as a list of categories to exclude. Defaults to False.
        show_zeros (bool, optional): If True, traits with a value of 0 are included in the embed field. Defaults to True.
        sort_items (bool, optional): If True, the items in the embed field are sorted alphabetically. Defaults to False.
    """
    embed_values = []
    if sort_items:
        char_traits = {k: sorted(v, key=lambda x: x[0]) for k, v in char_traits.items()}

    for category, traits in char_traits.items():
        if exclude_from_list and category.lower() in [x.lower() for x in categories_list]:
            continue
        if not exclude_from_list and category.lower() not in [x.lower() for x in categories_list]:
            continue

        formatted = []
        for trait, value, max_value, dots in traits:
            if (not show_zeros or category == "Disciplines") and value == 0:
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

    footer = f"Claimed by: {claimed_by.display_name} • " if claimed_by else ""
    footer += f"Last updated: {modified}"
    char_traits = character.all_trait_values

    embed = discord.Embed(title=f"{character.name}", description="", color=0x7777FF)
    embed.set_footer(text=footer)

    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined] # it exists
        if chronicle.current_date and character.date_of_birth:
            age = arrow.get(chronicle.current_date) - arrow.get(character.date_of_birth)
            embed.add_field(name="Age", value=f"`{age.days // 365}`", inline=True)
    except ValueError:
        pass

    embed.add_field(name="Class", value=character.class_name, inline=True)
    embed.add_field(name="Demeanor", value=character.demeanor, inline=True)
    embed.add_field(name="Nature", value=character.nature, inline=True)

    if character.class_name.lower() == "vampire":
        embed.add_field(name="Clan", value=f"{character.clan.name}", inline=True)
        embed.add_field(name="Generation", value=f"{character.generation}", inline=True)
        embed.add_field(name="Sire", value=f"{character.sire}", inline=True)

    if character.class_name.lower() == "mage":
        embed.add_field(name="Tradition", value=f"{character.tradition}", inline=True)
        embed.add_field(name="Essence", value=f"{character.essence}", inline=True)

    if character.class_name.lower() == "werewolf":
        embed.add_field(name="Tribe", value=f"{character.tribe}", inline=True)
        embed.add_field(name="Auspice", value=f"{character.auspice}", inline=True)
        embed.add_field(name="Breed", value=f"{character.breed}", inline=True)

    embed.add_field(name="\u200b", value="**ATTRIBUTES**", inline=False)
    for category, traits in __build_trait_display(char_traits, ["physical", "social", "mental"]):
        embed.add_field(name=category, value=traits, inline=True)

    embed.add_field(name="\u200b", value="**ABILITIES**", inline=False)
    for category, traits in __build_trait_display(
        char_traits, ["talents", "skills", "knowledges"], sort_items=True
    ):
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
        ],
        exclude_from_list=True,
    ):
        embed.add_field(name=category, value=traits, inline=True)

    return embed


def __embed2(
    character: Character,
    claimed_by: discord.User | None = None,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    custom_sections = character.custom_sections
    modified = arrow.get(character.modified).humanize()

    footer = f"Claimed by: {claimed_by.display_name} • " if claimed_by else ""
    footer += f"Last updated: {modified}"

    embed = discord.Embed(title=f"{character.name} - Page 2", description="", color=0x7777FF)

    embed.set_footer(text=footer)

    embed.add_field(name="Class", value=character.class_name, inline=True)

    if character.class_name.lower() == "vampire" and character.clan:
        embed.add_field(name="Clan", value=character.clan.name, inline=True)

    embed.add_field(name="\u200b", value="**EXPERIENCE**", inline=False)
    embed.add_field(name="Experience", value=f"`{character.experience}`", inline=True)
    embed.add_field(
        name="Lifetime Experience", value=f"`{character.experience_total}`", inline=True
    )
    embed.add_field(name="Lifetime Cool Points", value=f"`{character.cool_points}`", inline=True)

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
    embed2 = __embed2(character, claimed_by)

    paginator = pages.Paginator(pages=[embed1, embed2])  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)
