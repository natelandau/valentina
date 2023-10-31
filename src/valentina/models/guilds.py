"""Guild models.

Note, due to ForeignKey constraints, the Guild database model is defined in database.py.
"""
from datetime import datetime

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import GUILD_DEFAULTS
from valentina.utils import errors
from valentina.utils.helpers import time_now

from .sqlite_models import Guild, RollThumbnail


class GuildService:
    """Manage guilds in the database. Guilds are created on bot connect."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.settings_cache: dict[int, dict[str, str | int | bool]] = {}
        self.roll_result_thumbs: dict[int, dict[str, list[str]]] = {}
        self.changelog_versions_cache: list[str] = []

    async def add_roll_result_thumb(
        self, ctx: discord.ApplicationContext, roll_type: str, url: str
    ) -> None:
        """Add a roll result thumbnail to the database.

        This function fetches the user from the bot's user service, removes any existing thumbnail
        for the guild, and then adds a new thumbnail to the RollThumbnail database table.

        Args:
            ctx (discord.ApplicationContext): The context in which the command was invoked.
            roll_type (str): The type of roll for which the thumbnail is being added.
            url (str): The URL of the thumbnail image.

        Raises:
            errors.ValidationError: If the thumbnail already exists in the database.

        Returns:
            None
        """
        await self.bot.user_svc.update_or_add(ctx)  # type: ignore [attr-defined] # it really is defined

        self.roll_result_thumbs.pop(ctx.guild.id, None)

        already_exists = RollThumbnail.get_or_none(guild=ctx.guild.id, url=url)
        if already_exists:
            msg = "That thumbnail already exists"
            raise errors.ValidationError(msg)

        RollThumbnail.create(guild=ctx.guild.id, user=ctx.author.id, url=url, roll_type=roll_type)
        logger.info(f"DATABASE: Add roll result thumbnail for '{ctx.author.display_name}'")
