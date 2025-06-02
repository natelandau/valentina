"""Combinations of views and embeds for common actions."""

import discord

from valentina.constants import EmbedColor, EmojiDict, LogLevel
from valentina.discord.bot import ValentinaContext
from valentina.discord.views import ConfirmCancelButtons, present_embed


async def confirm_action(  # noqa: PLR0913
    ctx: ValentinaContext,
    title: str,
    description: str | None = None,
    hidden: bool = False,
    image: str | None = None,
    thumbnail: str | None = None,
    footer: str | None = None,
    audit: bool = False,
) -> tuple[bool, discord.Interaction, discord.Embed]:
    """Prompt the user for confirmation.

    Args:
        ctx (ValentinaContext): The context object.
        title (str): The title for the confirmation embed.
        description (str, optional): The description for the confirmation embed. Defaults to None.
        hidden (bool): Whether to make the response visible only to the user.
        image (str, optional): The image URL for the confirmation embed. Defaults to None.
        thumbnail (str, optional): The thumbnail URL for the confirmation embed. Defaults to None.
        footer: str | None = None,
        audit (bool): Whether to log the command in the audit log.

    Returns:
        tuple(bool, discord.InteractionMessage): A tuple containing the user's response and success response coroutine.
    """
    title = title + "?" if not title.endswith("?") else title

    view = ConfirmCancelButtons(ctx.author)
    msg = await present_embed(
        ctx,
        title=title,
        description=description,
        view=view,
        ephemeral=hidden,
        image=image,
        thumbnail=thumbnail,
        footer=footer,
    )
    await view.wait()
    if not view.confirmed:
        embed = discord.Embed(
            title=f"{EmojiDict.CANCEL} Cancelled",
            description=title.rstrip("?"),
            color=EmbedColor.WARNING.value,
        )
        await msg.edit_original_response(embed=embed, view=None)
        return (False, msg, None)

    response_embed = discord.Embed(
        title=title.rstrip("?"),
        description=description,
        color=EmbedColor.SUCCESS.value,
    )
    if image is not None:
        response_embed.set_image(url=image)

    if thumbnail is not None:
        response_embed.set_thumbnail(url=thumbnail)

    if footer is not None:
        response_embed.set_footer(text=footer)

    if audit:
        await ctx.post_to_audit_log(title.rstrip("?"))
    else:
        ctx.log_command(title.rstrip("?"), LogLevel.DEBUG)

    return (True, msg, response_embed)
