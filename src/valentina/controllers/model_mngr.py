"""Helper functions for managing Valentinamodels."""

from beanie import DeleteRules

from valentina.models import Character, Guild, User

from .channel_mngr import ChannelManager


async def delete_character(character: Character) -> None:
    """Delete a character and all associated data from the database, S3 storage, and Discord.

    Remove the character from its owner's character list, delete all associated images from
    storage, delete the character channel in Discord, and delete the character document with all linked data from the database.

    Args:
        character (Character): The character document to delete.

    Returns:
        None
    """
    guild = await Guild.get(character.guild, fetch_links=True)
    channel_manager = ChannelManager(guild)
    await channel_manager.delete_character_channel(character)

    user = await User.get(str(character.user_owner), fetch_links=True)
    await user.remove_character(character)
    await user.save()

    await character.delete_all_images()
    await character.delete(link_rule=DeleteRules.DELETE_LINKS)
