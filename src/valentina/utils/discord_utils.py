"""Helper utilities for working with the discord API."""

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import ChannelPermission
from valentina.dataclasses import ChannelObjects
from valentina.models import Campaign, CampaignBook, Character
from valentina.utils import errors

from .errors import BotMissingPermissionsError

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


async def assert_permissions(ctx: "ValentinaContext", **permissions: bool) -> None:  # noqa: RUF029
    """Check if the bot has the required permissions to run the command."""
    if missing := [
        perm for perm, value in permissions.items() if getattr(ctx.app_permissions, perm) != value
    ]:
        raise BotMissingPermissionsError(missing)


async def create_storyteller_role(guild: discord.Guild) -> discord.Role:
    """Create a storyteller role for the guild."""
    storyteller = discord.utils.get(guild.roles, name="Storyteller")

    if storyteller is None:
        storyteller = await guild.create_role(
            name="Storyteller",
            color=discord.Color.dark_teal(),
            mentionable=True,
            hoist=True,
        )

    perms = discord.Permissions()
    perms.update(
        add_reactions=True,
        attach_files=True,
        can_create_instant_invite=True,
        change_nickname=True,
        connect=True,
        create_private_threads=True,
        create_public_threads=True,
        embed_links=True,
        external_emojis=True,
        external_stickers=True,
        manage_messages=True,
        manage_threads=True,
        mention_everyone=True,
        read_message_history=True,
        read_messages=True,
        send_messages_in_threads=True,
        send_messages=True,
        send_tts_messages=True,
        speak=True,
        stream=True,
        use_application_commands=True,
        use_external_emojis=True,
        use_external_stickers=True,
        use_slash_commands=True,
        use_voice_activation=True,
        view_channel=True,
    )
    await storyteller.edit(reason=None, permissions=perms)
    logger.debug(f"CONNECT: {storyteller.name} role created/updated on {guild.name}")

    return storyteller


async def create_player_role(guild: discord.Guild) -> discord.Role:
    """Create player role for the guild."""
    player = discord.utils.get(guild.roles, name="Player", mentionable=True, hoist=True)

    if player is None:
        player = await guild.create_role(
            name="Player",
            color=discord.Color.dark_blue(),
            mentionable=True,
            hoist=True,
        )

    perms = discord.Permissions()
    perms.update(
        add_reactions=True,
        attach_files=True,
        can_create_instant_invite=True,
        change_nickname=True,
        connect=True,
        create_private_threads=True,
        create_public_threads=True,
        embed_links=True,
        external_emojis=True,
        external_stickers=True,
        mention_everyone=True,
        read_message_history=True,
        read_messages=True,
        send_messages_in_threads=True,
        send_messages=True,
        send_tts_messages=True,
        speak=True,
        stream=True,
        use_application_commands=True,
        use_external_emojis=True,
        use_external_stickers=True,
        use_slash_commands=True,
        use_voice_activation=True,
        view_channel=True,
    )
    await player.edit(reason=None, permissions=perms)
    logger.debug(f"CONNECT: {player.name} role created/updated on {guild.name}")

    return player


def set_channel_perms(requested_permission: ChannelPermission) -> discord.PermissionOverwrite:
    """Translate a ChannelPermission enum to a discord.PermissionOverwrite object.

    Takes a requested channel permission represented as an enum and
    sets the properties of a discord.PermissionOverwrite object
    to match those permissions.

    Args:
        requested_permission (ChannelPermission): The channel permission enum.

    Returns:
        discord.PermissionOverwrite: Permission settings as a Discord object.
    """
    # Map each ChannelPermission to the properties that should be False
    permission_mapping: dict[ChannelPermission, dict[str, bool]] = {
        ChannelPermission.HIDDEN: {
            "add_reactions": False,
            "manage_messages": False,
            "read_messages": False,
            "send_messages": False,
            "view_channel": False,
            "read_message_history": False,
        },
        ChannelPermission.READ_ONLY: {
            "add_reactions": True,
            "manage_messages": False,
            "read_messages": True,
            "send_messages": False,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": False,
        },
        ChannelPermission.POST: {
            "add_reactions": True,
            "manage_messages": False,
            "read_messages": True,
            "send_messages": True,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": True,
        },
        ChannelPermission.MANAGE: {
            "add_reactions": True,
            "manage_messages": True,
            "read_messages": True,
            "send_messages": True,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": True,
        },
    }

    # Create a permission overwrite object
    perms = discord.PermissionOverwrite()
    # Update the permission overwrite object based on the enum
    for key, value in permission_mapping.get(requested_permission, {}).items():
        setattr(perms, key, value)

    return perms


async def fetch_channel_object(
    ctx: discord.ApplicationContext | discord.AutocompleteContext | commands.Context,
    raise_error: bool = True,
    need_book: bool = False,
    need_character: bool = False,
    need_campaign: bool = False,
) -> ChannelObjects:
    """Determine the type of channel the command was invoked in.

    Args:
        ctx (discord.ApplicationContext|discord.AutocompleteContext): The context containing the channel object.
        need_character (bool, optional): Whether to raise an error if no character is found. Defaults to False.
        need_book (bool, optional): Whether to raise an error if no book is found. Defaults to False.
        need_campaign (bool, optional): Whether to raise an error if no campaign is found. Defaults to False.
        raise_error (bool, optional): Whether to raise an error if no active campaign is found. Defaults to True. Returns None if False.

    Returns:
        ChannelObjects: The channel objects found in the channel.

    Raises:
        errors.ChannelTypeError: If no active objects are found for the channel.
    """
    discord_channel = (
        ctx.interaction.channel if isinstance(ctx, discord.AutocompleteContext) else ctx.channel
    )

    channel_category = discord_channel.category

    campaign = await Campaign.find_one(
        Campaign.channel_campaign_category == channel_category.id, fetch_links=True
    )
    book = await CampaignBook.find_one(CampaignBook.channel == discord_channel.id, fetch_links=True)
    character = await Character.find_one(Character.channel == discord_channel.id, fetch_links=True)

    if raise_error and need_character and not character:
        msg = "Rerun command in a character channel."
        raise errors.ChannelTypeError(msg)

    if raise_error and need_campaign and not campaign:
        msg = "Rerun command in a channel associated with a campaign"
        raise errors.ChannelTypeError(msg)

    if raise_error and need_book and not book:
        msg = "Rerun command in a book channel"
        raise errors.ChannelTypeError(msg)

    if raise_error and not campaign and not book and not character:
        raise errors.ChannelTypeError

    return ChannelObjects(campaign=campaign, book=book, character=character)
