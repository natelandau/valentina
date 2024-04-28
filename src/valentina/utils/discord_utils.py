"""Helper utilities for working with the discord API."""

import discord
from loguru import logger

from valentina.constants import ChannelPermission

from .errors import BotMissingPermissionsError


async def assert_permissions(ctx: discord.ApplicationContext, **permissions: bool) -> None:  # noqa: RUF029
    """Check if the bot has the required permissions to run the command.""."""
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
