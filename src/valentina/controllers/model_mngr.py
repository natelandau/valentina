"""Helper functions for managing Valentinamodels."""

from beanie import DeleteRules
from loguru import logger

from valentina.models import Character, User

from .channel_mngr import ChannelManager


async def delete_character(character: Character) -> None:
    """Delete a character and all associated data from the database, S3 storage, and Discord.

    Remove the character from its owner's character list, delete all associated images from
    storage, delete the character channel in Discord, and delete the character document with all linked data from the database.

    NOTE: Posting to the audit log is not handled here, as discord and web functionality differ.

    Args:
        character (Character): The character document to delete.

    Returns:
        None
    """
    from valentina.bot import bot  # noqa: PLC0415

    guild = await bot.get_guild_from_id(character.guild)

    channel_manager = ChannelManager(guild)
    await channel_manager.delete_character_channel(character)

    user = await User.get(str(character.user_owner), fetch_links=True)
    await user.remove_character(character)
    await user.save()

    await character.delete_all_images()
    await character.delete(link_rule=DeleteRules.DELETE_LINKS)
    logger.info(f"Deleted character {character.name} from guild {guild.name}")
