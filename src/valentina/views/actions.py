"""Combinations of views and embeds for common actions."""

from collections.abc import Coroutine

import discord

from valentina.constants import EmbedColor, Emoji
from valentina.models.bot import ValentinaContext
from valentina.views import ConfirmCancelButtons, present_embed


async def confirm_action(
    ctx: ValentinaContext,
    title: str,
    description: str | None = None,
    hidden: bool = False,
    image: str | None = None,
    thumbnail: str | None = None,
    footer: str | None = None,
    delete_after_confirmation: bool = False,
) -> tuple[bool, Coroutine]:
    """Prompt the user for confirmation.

    Args:
        ctx (ValentinaContext): The context object.
        title (str): The title for the confirmation embed.
        description (str, optional): The description for the confirmation embed. Defaults to None.
        hidden (bool): Whether to make the response visible only to the user.
        image (str, optional): The image URL for the confirmation embed. Defaults to None.
        thumbnail (str, optional): The thumbnail URL for the confirmation embed. Defaults to None.
        footer: str | None = None,
        delete_after_confirmation (bool): Whether to delete the message after the user confirms. Useful for beginning new interactions. Defaults to False.

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
            title=f"{Emoji.CANCEL.value} Cancelled",
            description=title.rstrip("?"),
            color=EmbedColor.WARNING.value,
        )
        await msg.edit_original_response(embed=embed, view=None)
        return (False, None)

    response_embed = discord.Embed(
        title=title.rstrip("?"), description=description, color=EmbedColor.SUCCESS.value
    )
    if image is not None:
        (response_embed.set_image(url=image),)

    if thumbnail is not None:
        (response_embed.set_thumbnail(url=thumbnail),)

    if footer is not None:
        (response_embed.set_footer(text=footer),)

    if delete_after_confirmation:
        response = msg.delete_original_response()
    else:
        response = msg.edit_original_response(embed=response_embed, view=None)  # type: ignore [assignment]

    return (True, response)
