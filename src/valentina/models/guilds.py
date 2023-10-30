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

    def fetch_storyteller_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the storyteller channel for the guild from the settings.

        Fetch the guild's settings to determine if a storyteller channel has been set.
        If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the storyteller channel for.

        Returns:
            discord.TextChannel|None: The storyteller channel, if it exists and is set; otherwise, None.
        """
        settings = self.fetch_guild_settings(guild)
        db_id = settings.get("storyteller_channel_id", None)

        if db_id:
            return discord.utils.get(guild.text_channels, id=settings["storyteller_channel_id"])

        return None

    def fetch_roll_result_thumbs(self, ctx: discord.ApplicationContext) -> dict[str, list[str]]:
        """Get all roll result thumbnails for a guild.

        This function first checks if the thumbnails for the guild are already cached.
        If not, it fetches the thumbnails from the RollThumbnail database table and caches them.

        Args:
            ctx (discord.ApplicationContext): The context in which the command was invoked.

        Returns:
            dict[str, List[str]]: A dictionary mapping roll types to lists of thumbnail URLs.
        """
        # Fetch from cache if it exists
        if ctx.guild.id in self.roll_result_thumbs:
            logger.debug(f"CACHE: Fetch roll result thumbnails for '{ctx.guild.name}'")
            return self.roll_result_thumbs[ctx.guild.id]

        # Fetch from database
        logger.debug(f"DATABASE: Fetch roll result thumbnails for '{ctx.guild.name}'")
        self.roll_result_thumbs[ctx.guild.id] = {}

        for thumb in RollThumbnail.select().where(RollThumbnail.guild == ctx.guild.id):
            if thumb.roll_type not in self.roll_result_thumbs[ctx.guild.id]:
                self.roll_result_thumbs[ctx.guild.id][thumb.roll_type] = [thumb.url]
            else:
                self.roll_result_thumbs[ctx.guild.id][thumb.roll_type].append(thumb.url)

        return self.roll_result_thumbs[ctx.guild.id]

    def purge_cache(
        self,
        ctx: discord.ApplicationContext | discord.AutocompleteContext | None = None,
        guild: discord.Guild | None = None,
    ) -> None:
        """Purge the cache for a guild or all guilds.

        Args:
            ctx (optional, ApplicationContext | AutocompleteContext): The application context.
            guild (optional, discord.Guild): The guild to purge the cache for.
        """
        if ctx and not guild:
            guild = (
                ctx.guild if isinstance(ctx, discord.ApplicationContext) else ctx.interaction.guild
            )

        if ctx or guild:
            self.settings_cache.pop(guild.id, None)
            self.roll_result_thumbs.pop(guild.id, None)
            self.changelog_versions_cache = []
            logger.debug(f"CACHE: Purge guild cache for '{guild.name}'")
        else:
            self.settings_cache = {}
            self.roll_result_thumbs = {}
            self.changelog_versions_cache = []
            logger.debug("CACHE: Purge all guild caches")

    def update_or_add(
        self,
        guild: discord.Guild | None = None,
        ctx: discord.ApplicationContext | None = None,
        updates: dict[str, str | int | bool] | None = None,
    ) -> Guild:
        """Add a guild to the database or update it if it already exists."""
        if (ctx and guild) or (not ctx and not guild):
            msg = "Need to pass either a guild or a context"
            raise ValueError(msg)

        # Purge the guild from the cache
        if ctx:
            self.purge_cache(ctx)
            guild = ctx.guild
        elif guild:
            self.purge_cache(guild=guild)

        # Create initialization data
        initial_data = GUILD_DEFAULTS.copy() | {"modified": str(time_now())} | (updates or {})

        db_guild, is_created = Guild.get_or_create(
            id=guild.id,
            defaults={
                "name": guild.name,
                "created": time_now(),
                "data": initial_data,
            },
        )

        if is_created:
            logger.info(f"DATABASE: Created guild: `{db_guild.name}`")
        elif updates:
            logger.debug(f"DATABASE: Updated guild: `{db_guild.name}`")
            updates["modified"] = str(time_now())

            for key, value in updates.items():
                logger.debug(f"DATABASE: Update guild: `{db_guild.name}`: `{key}` to `{value}`")

            # Make requested updates to the guild
            Guild.update(data=Guild.data.update(updates)).where(Guild.id == guild.id).execute()

            # Ensure default data values are set
            Guild.get_by_id(guild.id).set_default_data_values()

        return Guild.get_by_id(guild.id)
