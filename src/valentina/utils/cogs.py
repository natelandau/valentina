"""Helpers for working with cogs."""
import discord

from valentina.constants import EmbedColor
from valentina.views import ConfirmCancelButtons, present_embed


async def confirm_action(
    ctx: discord.ApplicationContext,
    title: str,
    description: str | None = None,
    hidden: bool = False,
) -> tuple[bool, discord.Interaction]:
    """Prompt the user for confirmation.

    Args:
        ctx (discord.ApplicationContext): The context object.
        title (str): The title for the confirmation embed.
        description (str, optional): The description for the confirmation embed. Defaults to None.
        hidden (bool): Whether to make the response visible only to the user.

    Returns:
        tuple(bool, discord.Message): A tuple containing the user's response and the message object.
    """
    title = title + "?" if not title.endswith("?") else title

    view = ConfirmCancelButtons(ctx.author)
    msg = await present_embed(
        ctx, title=title, description=description, view=view, ephemeral=hidden
    )
    await view.wait()
    if not view.confirmed:
        embed = discord.Embed(title="Cancelled", color=EmbedColor.WARNING.value)
        await msg.edit_original_response(embed=embed, view=None)
        return (False, msg)

    return (True, msg)
