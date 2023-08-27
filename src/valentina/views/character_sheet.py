"""View a character sheet."""
from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina.models.db_tables import Character
from valentina.models.statistics import Statistics
from valentina.utils import errors

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
    owned_by_user: discord.User | None = None,
    title: str | None = None,
) -> discord.Embed:
    """Builds the first embed of a character sheet. This embed contains the character's name, class, experience, cool points, and attributes and abilities."""
    modified = arrow.get(character.data["modified"]).humanize()

    if title is None:
        title = character.name

    footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
    footer += f"Last updated: {modified}"
    char_traits = character.all_trait_values

    embed = discord.Embed(title=title, description="", color=0x7777FF)
    embed.set_footer(text=footer)

    try:
        campaign = ctx.bot.campaign_svc.fetch_active(ctx)  # type: ignore [attr-defined] # it exists
        if campaign.current_date and character.data.get("date_of_birth"):
            age = arrow.get(campaign.current_date) - arrow.get(character.data["date_of_birth"])
            embed.add_field(name="Age", value=f"`{age.days // 365}`", inline=True)
    except errors.NoActiveCampaignError:
        pass

    embed.add_field(name="Class", value=character.class_name, inline=True)
    embed.add_field(
        name="Demeanor",
        value=character.data["demeanor"] if character.data.get("demeanor") else "",
        inline=True,
    )
    embed.add_field(
        name="Nature",
        value=character.data["nature"] if character.data.get("nature") else "",
        inline=True,
    )

    if character.class_name.lower() == "vampire":
        embed.add_field(name="Clan", value=f"{character.clan.name}", inline=True)
        embed.add_field(name="Generation", value=f"{character.data['generation']}", inline=True)
        embed.add_field(name="Sire", value=f"{character.data['sire']}", inline=True)

    if character.class_name.lower() == "mage":
        embed.add_field(name="Tradition", value=f"{character.data['tradition']}", inline=True)
        embed.add_field(name="Essence", value=f"{character.data['essence']}", inline=True)

    if character.class_name.lower() == "werewolf":
        embed.add_field(name="Tribe", value=f"{character.data['tribe']}", inline=True)
        embed.add_field(name="Auspice", value=f"{character.data['auspice']}", inline=True)
        embed.add_field(name="Breed", value=f"{character.data['breed']}", inline=True)

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
    ctx: discord.ApplicationContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    custom_sections = character.custom_sections
    modified = arrow.get(character.data["modified"]).humanize()

    if title is None:
        title = f"{character.name} - Page 2"

    footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
    footer += f"Last updated: {modified}"

    embed = discord.Embed(title=title, description="", color=0x7777FF)

    embed.set_footer(text=footer)

    embed.add_field(name="Class", value=character.class_name, inline=True)

    if character.class_name.lower() == "vampire" and character.clan:
        embed.add_field(name="Clan", value=character.clan.name, inline=True)

    embed.add_field(name="\u200b", value="**EXPERIENCE**", inline=False)
    embed.add_field(name="Experience", value=f"`{character.data['experience']}`", inline=True)
    embed.add_field(
        name="Lifetime Experience", value=f"`{character.data['experience_total']}`", inline=True
    )
    embed.add_field(
        name="Lifetime Cool Points", value=f"`{character.data['cool_points_total']}`", inline=True
    )

    if character.data.get("bio"):
        embed.add_field(
            name=f"**About {character.name}**", value=character.data["bio"], inline=False
        )

    if len(custom_sections) > 0:
        embed.add_field(name="\u200b", value="**CUSTOM SECTIONS**", inline=False)
        for section in custom_sections:
            embed.add_field(
                name=f"__**{section.title.upper()}**__", value=section.description, inline=True
            )

    stats = Statistics(ctx, character=character)
    embed.add_field(
        name="\u200b", value=f"**ROLL STATISTICS**{stats.get_text(with_title=False)}", inline=False
    )

    return embed


async def show_sheet(
    ctx: discord.ApplicationContext,
    character: Character,
    ephemeral: Any = False,
) -> Any:
    """Show a character sheet."""
    print(character.owned_by)
    owned_by_user = discord.utils.get(ctx.bot.users, id=character.owned_by.id)
    embeds = []
    embeds.append(__embed1(ctx, character, owned_by_user))
    embeds.append(__embed2(ctx, character, owned_by_user))

    paginator = pages.Paginator(pages=embeds)  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)


async def sheet_embed(
    ctx: discord.ApplicationContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
) -> discord.Embed:
    """Return the first page of the sheet as an embed."""
    owned_by_user = discord.utils.get(ctx.bot.users, id=character.owned_by)
    return __embed1(ctx, character, owned_by_user=owned_by_user, title=title)
