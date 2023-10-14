"""View a character sheet."""
from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina.constants import CharSheetSection, Emoji, TraitCategories
from valentina.models.db_tables import Character
from valentina.models.statistics import Statistics
from valentina.utils import errors

MAX_DOT_DISPLAY = 6


def __build_trait_display(
    char_traits: dict[str, Any],
    categories_list: list[TraitCategories],
    show_zeros: bool = True,
    sort_items: bool = False,
) -> list[tuple[str, str]]:
    """Builds the name and value for an embed field representing a category of traits.

    Args:
        char_traits (dict[str, Any]): A dictionary of character traits.
        categories_list (list[str]): A list of categories to include in the embed field.
        show_zeros (bool, optional): If True, traits with a value of 0 are included in the embed field. Defaults to True.
        sort_items (bool, optional): If True, the items in the embed field are sorted alphabetically. Defaults to False.
    """
    embed_values = []
    if sort_items:
        char_traits = {k: sorted(v, key=lambda x: x[0]) for k, v in char_traits.items()}

    for category, traits in char_traits.items():
        if category not in [x.name for x in categories_list]:
            continue

        formatted = []
        for trait, value, max_value, dots in traits:
            trait_category = TraitCategories[category]
            if (not show_zeros or not trait_category.value["show_zero"]) and value == 0:
                continue
            if max_value > MAX_DOT_DISPLAY:
                formatted.append(f"`{trait:13}: {value}/{max_value}`")
            else:
                formatted.append(f"`{trait:13}: {dots}`")

        embed_values.append((category.title(), "\n".join(formatted)))

    return embed_values


def __embed1(  # noqa: C901, PLR0912
    ctx: discord.ApplicationContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    desc_prefix: str | None = None,
    desc_suffix: str | None = None,
    show_footer: bool = True,
) -> discord.Embed:
    """Builds the first embed of a character sheet. This embed contains the character's name, class, experience, cool points, and attributes and abilities."""
    modified = arrow.get(character.data["modified"]).humanize()

    if title is None:
        title = character.name

    if show_footer:
        footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
        footer += f"Last updated: {modified}"

    char_traits = character.all_trait_values

    embed = discord.Embed(title=title, description=desc_prefix, color=0x7777FF)
    embed.set_footer(text=footer)

    try:
        campaign = ctx.bot.campaign_svc.fetch_active(ctx)  # type: ignore [attr-defined] # it exists
        if campaign.current_date and character.data.get("date_of_birth"):
            age = arrow.get(campaign.current_date) - arrow.get(character.data["date_of_birth"])
            embed.add_field(name="Age", value=f"`{age.days // 365}`", inline=True)
    except errors.NoActiveCampaignError:
        pass

    embed.add_field(
        name="Alive",
        value=Emoji.ALIVE.value if character.data.get("is_alive", True) else Emoji.DEAD.value,
    )

    embed.add_field(name="Class", value=f"{character.class_name.title()}", inline=True)

    if character.class_name.lower() in ["mortal", "hunter", "human"]:
        embed.add_field(name="Concept", value=character.data.get("concept_human", ""), inline=True)

    if character.class_name.lower() == "vampire":
        embed.add_field(name="Clan", value=character.clan.name, inline=True)
        embed.add_field(name="Generation", value=character.data.get("generation", ""), inline=True)
        embed.add_field(name="Sire", value=character.data.get("sire", ""), inline=True)

    if character.class_name.lower() == "mage":
        embed.add_field(name="Tradition", value=character.data.get("tradition", ""), inline=True)
        embed.add_field(name="Essence", value=character.data.get("essence", ""), inline=True)

    if character.class_name.lower() == "werewolf":
        embed.add_field(name="Tribe", value=character.data.get("tribe", ""), inline=True)
        embed.add_field(name="Auspice", value=character.data.get("auspice", ""), inline=True)
        embed.add_field(name="Breed", value=character.data.get("breed", ""), inline=True)

    # Add the trait sections to the sheet
    for section in sorted(CharSheetSection, key=lambda x: x.value["order"]):
        if section != CharSheetSection.NONE:
            embed.add_field(
                name="\u200b",
                value=f"**{section.name.upper()}**",
                inline=False,
            )
        for category, traits in __build_trait_display(
            char_traits,
            [tc for tc in TraitCategories if tc.value["section"] == section],
        ):
            embed.add_field(name=category, value=traits, inline=True)

    if desc_suffix:
        embed.add_field(name="\u200b", value=desc_suffix, inline=False)

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

    if character.data.get("bio"):
        embed.add_field(name="**BIOGRAPHY**", value=character.data["bio"], inline=False)

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


def __image_embed(
    ctx: discord.ApplicationContext,
    character: Character,
    image_key: str,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    modified = arrow.get(character.data["modified"]).humanize()

    if title is None:
        title = f"{character.name} - Images"

    footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
    footer += f"Last updated: {modified}"

    embed = discord.Embed(title=title, description="", color=0x7777FF)

    embed.set_footer(text=footer)

    image_url = ctx.bot.aws_svc.get_url(image_key)  # type: ignore [attr-defined] # it exists
    embed.set_image(url=image_url)

    return embed


async def show_sheet(
    ctx: discord.ApplicationContext,
    character: Character,
    ephemeral: Any = False,
) -> Any:
    """Show a character sheet."""
    owned_by_user = discord.utils.get(ctx.bot.users, id=character.owned_by.user)
    embeds = []
    embeds.extend(
        [__embed1(ctx, character, owned_by_user), __embed2(ctx, character, owned_by_user)]
    )

    image_keys = character.data.get("images", None)

    if image_keys:
        embeds.extend(
            [__image_embed(ctx, character, image_key, owned_by_user) for image_key in image_keys]
        )

    paginator = pages.Paginator(pages=embeds)  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)


async def sheet_embed(
    ctx: discord.ApplicationContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    desc_prefix: str | None = None,
    desc_suffix: str | None = None,
) -> discord.Embed:
    """Return the first page of the sheet as an embed."""
    owned_by_user = discord.utils.get(ctx.bot.users, id=character.owned_by.user)
    return __embed1(
        ctx,
        character,
        owned_by_user=owned_by_user,
        title=title,
        desc_prefix=desc_prefix,
        desc_suffix=desc_suffix,
    )
