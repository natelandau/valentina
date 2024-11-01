"""Helper utilities for working with the discord API."""

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import CampaignChannelName, ChannelPermission
from valentina.discord.dataclasses import ChannelObjects
from valentina.models import Campaign, CampaignBook, Character
from valentina.utils import errors

if TYPE_CHECKING:
    from valentina.discord.bot import ValentinaContext


async def assert_permissions(
    ctx: "ValentinaContext", **permissions: bool
) -> None:  # pragma: no cover
    """Check if the bot has the required permissions to run the command.

    Verify that the bot has the necessary permissions specified in the permissions argument.
    Raise an error if any required permissions are missing.

    Args:
        ctx (ValentinaContext): The context object containing the bot's permissions.
        **permissions (bool): Key-value pairs of permissions to check. Keys are permission
            names and values are the required states (True/False).

    Raises:
        BotMissingPermissionsError: If any required permissions are missing.
    """
    if missing := [
        perm for perm, value in permissions.items() if getattr(ctx.app_permissions, perm) != value
    ]:
        raise errors.BotMissingPermissionsError(missing)


async def create_storyteller_role(guild: discord.Guild) -> discord.Role:  # pragma: no cover
    """Create or update the storyteller role for the guild.

    Create a "Storyteller" role if it doesn't exist, or update its permissions if it does.
    The role is given specific permissions suitable for a storyteller in a role-playing game context.

    Args:
        guild (discord.Guild): The Discord guild to create or update the role in.

    Returns:
        discord.Role: The created or updated "Storyteller" role.
    """
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


async def create_player_role(guild: discord.Guild) -> discord.Role:  # pragma: no cover
    """Create or update the Player role in a Discord guild.

    This function creates a new Player role if it doesn't exist, or updates an existing one.
    The role is set with specific permissions suitable for regular players in the game.

    Args:
        guild (discord.Guild): The Discord guild where the role should be created or updated.

    Returns:
        discord.Role: The created or updated Player role.
    """
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


def set_channel_perms(
    requested_permission: ChannelPermission,
) -> discord.PermissionOverwrite:  # pragma: no cover
    """Create a Discord PermissionOverwrite object based on the requested permission level.

    This function maps a ChannelPermission enum to a set of Discord permissions,
    creating a PermissionOverwrite object with the appropriate settings.

    Args:
        requested_permission (ChannelPermission): The desired permission level for the channel.

    Returns:
        discord.PermissionOverwrite: A PermissionOverwrite object with the permissions set
        according to the requested permission level.
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
) -> ChannelObjects:  # pragma: no cover
    """Determine the channel type and fetch associated objects.

    Identify the channel type and fetch related campaign, book, and character objects. Raise errors if specified conditions are not met.

    Args:
        ctx (discord.ApplicationContext | discord.AutocompleteContext | commands.Context): The context containing the channel object.
        raise_error (bool, optional): Whether to raise an error if no active objects are found. Defaults to True.
        need_book (bool, optional): Whether to raise an error if no book is found. Defaults to False.
        need_character (bool, optional): Whether to raise an error if no character is found. Defaults to False.
        need_campaign (bool, optional): Whether to raise an error if no campaign is found. Defaults to False.

    Returns:
        ChannelObjects: An object containing the campaign, book, character, and a flag for storyteller channel.

    Raises:
        errors.ChannelTypeError: If the required objects are not found based on the specified conditions.
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

    is_storyteller_channel = (
        discord_channel and discord_channel.name == CampaignChannelName.STORYTELLER.value
    )

    return ChannelObjects(
        campaign=campaign,
        book=book,
        character=character,
        is_storyteller_channel=is_storyteller_channel,
    )


def get_user_from_id(
    guild: discord.Guild, user_id: int
) -> discord.Member | None:  # pragma: no cover
    """Get a discord user object from a user ID.

    Args:
        guild (discord.Guild): The guild to get the user from.
        user_id (int): The ID of the user to get.

    Returns:
        discord.Member | None: The user with the given ID, or None if it is not found.
    """
    return discord.utils.get(guild.members, id=user_id)
