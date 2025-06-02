"""View a character sheet."""

from typing import Any

import arrow
import discord
from discord.ext import pages

from valentina.constants import MAX_DOT_DISPLAY, EmbedColor, InventoryItemType
from valentina.controllers import CharacterSheetBuilder, PermissionManager
from valentina.discord.bot import ValentinaContext
from valentina.models import AWSService, Character, Statistics


async def __embed1(  # noqa: PLR0913
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    desc_prefix: str | None = None,
    desc_suffix: str | None = None,
    show_footer: bool = True,
    is_storyteller: bool = False,
) -> discord.Embed:
    """Builds the first embed of a character sheet. This embed contains the character's name, class, experience, cool points, and attributes and abilities."""
    sheet_builder = CharacterSheetBuilder(character=character)
    profile_data = await sheet_builder.fetch_sheet_profile(storyteller_view=is_storyteller)

    if title is None:
        title = character.full_name

    embed = discord.Embed(title=title, description=desc_prefix, color=EmbedColor.INFO.value)

    if show_footer:
        modified = arrow.get(character.date_modified).humanize()
        footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
        footer += f"Last updated: {modified}"
        embed.set_footer(text=footer)

    for key, value in profile_data.items():
        embed.add_field(
            name=key,
            value=value,
        )

    sheet_data = sheet_builder.fetch_sheet_character_traits()
    for section in sheet_data:
        embed.add_field(
            name="\u200b",
            value=f"**{section.section.name.upper()}**",
            inline=False,
        )
        for category in section.categories:
            trait_values = [
                f"`{x.name:14}: {x.dots}`"
                if x.max_value <= MAX_DOT_DISPLAY
                else f"`{x.name:14}: {x.value}/{x.max_value}`"
                for x in category.traits
            ]
            if trait_values:
                embed.add_field(
                    name=category.category.name.title(),
                    value="\n".join(trait_values),
                    inline=True,
                )

    if desc_suffix:
        embed.add_field(name="\u200b", value=desc_suffix, inline=False)

    return embed


async def __embed2(
    ctx: ValentinaContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    show_footer: bool = True,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    custom_sections = character.sheet_sections
    items = character.inventory

    if title is None:
        title = f"{character.full_name} - Page 2"

    embed = discord.Embed(title=title, description="", color=EmbedColor.INFO.value)

    if show_footer:
        modified = arrow.get(character.date_modified).humanize()
        footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
        footer += f"Last updated: {modified}"
        embed.set_footer(text=footer)

    if character.bio:
        embed.add_field(name="**BIOGRAPHY**", value=character.bio, inline=False)

    if items:
        embed.add_field(name="\u200b", value="**INVENTORY**", inline=False)
        for member in InventoryItemType:
            sub_items = [i for i in items if i.type == member.name]  # type: ignore [attr-defined]
            content = ""
            for i in sub_items:
                line_begin = "- "
                name = f"**{i.name}**"  # type: ignore [attr-defined]
                desc = f": {i.description}" if i.description else ""  # type: ignore [attr-defined]
                line_end = "\n"
                content += f"{line_begin}{name}{desc}{line_end}"

            if sub_items:
                embed.add_field(name=f"__**{member.value}**__", value=content, inline=False)
    else:
        embed.add_field(name="**EMPTY INVENTORY**", value="No items in inventory", inline=False)

    if len(custom_sections) > 0:
        embed.add_field(name="\u200b", value="**CUSTOM SECTIONS**", inline=False)
        for section in custom_sections:
            embed.add_field(
                name=f"__**{section.title.title()}**__",
                value=section.content,
                inline=True,
            )

    stats = Statistics(ctx)
    statistic_text = await stats.character_statistics(character, as_embed=False, with_title=False)
    embed.add_field(
        name="\u200b",
        value=f"**ROLL STATISTICS**\n{statistic_text}",
        inline=False,
    )

    return embed


def __image_embed(
    character: Character,
    image_key: str,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    show_footer: bool = True,
) -> discord.Embed:
    """Builds the second embed of a character sheet. This embed contains the character's bio and custom sections."""
    if title is None:
        title = f"{character.full_name} - Images"

    embed = discord.Embed(title=title, description="", color=0x7777FF)

    if show_footer:
        modified = arrow.get(character.date_modified).humanize()
        footer = f"Owned by: {owned_by_user.display_name} • " if owned_by_user else ""
        footer += f"Last updated: {modified}"
        embed.set_footer(text=footer)

    aws_svc = AWSService()
    image_url = aws_svc.get_url(image_key)
    embed.set_image(url=image_url)

    return embed


async def show_sheet(
    ctx: ValentinaContext,
    character: Character,
    ephemeral: Any = False,
    show_footer: bool = True,
) -> Any:
    """Show a character sheet."""
    permission_mng = PermissionManager(ctx.guild.id)
    is_storyteller = await permission_mng.is_storyteller(ctx.author.id)

    owned_by_user = discord.utils.get(ctx.bot.users, id=character.user_owner)

    embeds = []
    embeds.extend(
        [
            await __embed1(
                character,
                owned_by_user,
                show_footer=show_footer,
                is_storyteller=is_storyteller,
            ),
            await __embed2(ctx, character, owned_by_user, show_footer=show_footer),
        ],
    )

    if character.images:
        embeds.extend(
            [
                __image_embed(character, image_key, owned_by_user, show_footer=show_footer)
                for image_key in character.images
            ],
        )

    paginator = pages.Paginator(pages=embeds)  # type: ignore [arg-type]
    paginator.remove_button("first")
    paginator.remove_button("last")
    await paginator.respond(ctx.interaction, ephemeral=ephemeral)


async def sheet_embed(  # noqa: PLR0913
    ctx: ValentinaContext,
    character: Character,
    owned_by_user: discord.User | None = None,
    title: str | None = None,
    desc_prefix: str | None = None,
    desc_suffix: str | None = None,
    show_footer: bool = True,
) -> discord.Embed:
    """Return the first page of the sheet as an embed."""
    permission_mng = PermissionManager(ctx.guild.id)
    is_storyteller = await permission_mng.is_storyteller(ctx.author.id)
    owned_by_user = discord.utils.get(ctx.bot.users, id=character.user_owner)
    return await __embed1(
        character,
        owned_by_user=owned_by_user,
        title=title,
        desc_prefix=desc_prefix,
        desc_suffix=desc_suffix,
        show_footer=show_footer,
        is_storyteller=is_storyteller,
    )
