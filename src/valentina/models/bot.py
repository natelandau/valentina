"""The main file for the Valentina bot."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
import semver
from beanie import UpdateResponse, init_beanie
from beanie.operators import Set
from discord.ext import commands
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from valentina.constants import EmbedColor
from valentina.models.mongo_collections import (
    Campaign,
    CampaignChapter,
    CampaignExperience,
    CampaignNote,
    CampaignNPC,
    Character,
    CharacterTrait,
    GlobalProperty,
    Guild,
    User,
    UserMacro,
)
from valentina.utils import errors
from valentina.utils.changelog_parser import ChangelogParser


async def init_database(config: dict) -> None:
    """Initialize the database."""
    # Create Motor client
    client = AsyncIOMotorClient(config["VALENTINA_MONGODB_URI"], tz_aware=True)

    # FIXME: Drop the database on every startup while in development
    logger.warning("Dropping database on startup")
    await client.drop_database(config["VALENTINA_MONGODB_DB"])

    # Initialize beanie with the Sample document class and a database
    await init_beanie(
        database=client[config["VALENTINA_MONGODB_DB"]],
        document_models=[
            Campaign,
            CampaignChapter,
            CampaignExperience,
            CampaignNote,
            CampaignNPC,
            Character,
            CharacterTrait,
            GlobalProperty,
            Guild,
            User,
            UserMacro,
        ],
    )


# Subclass discord.ApplicationContext to create custom application context
class ValentinaContext(discord.ApplicationContext):
    """A custom application context for Valentina."""

    def _message_to_embed(self, message: str) -> discord.Embed:  # pragma: no cover
        """Convert a string message to a discord embed.

        Args:
            message (str): The message to be converted.

        Returns:
            discord.Embed: The created embed.
        """
        # Set color based on command
        if hasattr(self, "command") and (
            self.command.qualified_name.startswith("admin")
            or self.command.qualified_name.startswith("owner")
            or self.command.qualified_name.startswith("developer")
        ):
            color = EmbedColor.WARNING.value
        elif hasattr(self, "command") and self.command.qualified_name.startswith("storyteller"):
            color = EmbedColor.SUCCESS.value
        elif hasattr(self, "command") and self.command.qualified_name.startswith("gameplay"):
            color = EmbedColor.GRAY.value
        elif hasattr(self, "command") and self.command.qualified_name.startswith("campaign"):
            color = EmbedColor.DEFAULT.value
        else:
            color = EmbedColor.INFO.value

        embed = discord.Embed(title=message, color=color)
        embed.timestamp = datetime.now()

        footer = ""
        if hasattr(self, "command"):
            footer += f"Command: /{self.command.qualified_name}"
        else:
            footer += "Command: Unknown"

        if hasattr(self, "author"):
            footer += f" | User: @{self.author.display_name}"
        if hasattr(self, "channel"):
            footer += f" | Channel: #{self.channel.name}"

        embed.set_footer(text=footer)

        return embed

    async def post_to_error_log(
        self, message: str | discord.Embed, error: Exception
    ) -> None:  # pragma: no cover
        """Send an error message or embed to the guild's error log channel.

        If the error log channel exists, convert the input message to an embed if it's a string and send it to the guild's error log channel.

        Args:
            ctx (discord.ApplicationContext): The context for the discord command.
            message (str|discord.Embed): The error message or embed to send to the channel.
            error (Exception): The exception that triggered the error log message.

        Raises:
            discord.DiscordException: If the error message could not be sent to the channel.
        """
        # Get the database guild object and error log channel
        guild = await Guild.get(self.guild.id)
        error_log_channel = guild.fetch_error_log_channel(self.guild)

        # Log to the error log channel if it exists and is enabled
        if error_log_channel:
            embed = self._message_to_embed(message) if isinstance(message, str) else message
            try:
                await error_log_channel.send(embed=embed)
            except discord.HTTPException:
                embed = discord.Embed(
                    title=f"A {error.__class__.__name__} exception was raised",
                    description="The error was too long to fit! Check the logs for full traceback",
                    color=EmbedColor.ERROR.value,
                    timestamp=discord.utils.utcnow(),
                )
                await error_log_channel.send(embed=embed)

    async def post_to_audit_log(self, message: str | discord.Embed) -> None:  # pragma: no cover
        """Send a message to the audit log channel for a guild.

        If a string is passed in, an embed will be created from it. If an embed is passed in, it will be sent as is.

        Args:
            ctx (discord.ApplicationContext): The context in which the command was invoked.
            message (str|discord.Embed): The message to be sent to the log channel.

        Raises:
            discord.DiscordException: If the message could not be sent.
        """
        # Get the database guild object and error log channel
        guild = await Guild.get(self.guild.id)
        audit_log_channel = guild.fetch_audit_log_channel(self.guild)

        if audit_log_channel:
            embed = self._message_to_embed(message) if isinstance(message, str) else message

            try:
                await audit_log_channel.send(embed=embed)
            except discord.HTTPException as e:
                raise errors.MessageTooLongError from e


class Valentina(commands.Bot):
    """Subclass discord.Bot."""

    def __init__(self, parent_dir: Path, config: dict, version: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.parent_dir = parent_dir
        self.config = config
        self.version = version
        self.owner_channels = [int(x) for x in self.config["VALENTINA_OWNER_CHANNELS"].split(",")]

        # Load Cogs
        # #######################
        for cog in Path(self.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                logger.info(f"COGS: Loading - {cog.stem}")
                self.load_extension(f"valentina.cogs.{cog.stem}")

    async def on_connect(self) -> None:
        """Perform early setup."""
        # Initialize the mongodb database
        await init_database(self.config)

        # TODO: BEGIN one-time migration code (remove after first run)
        from valentina.utils.migrate_to_mongo import Migrate

        migrate = Migrate(config=self.config)
        await migrate.do_migration()
        # TODO: END: Remove one-time migration code

        # Connect to discord
        if not self.connected:
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            logger.info(
                f"CONNECT: Playing on {len(self.guilds)} servers",
            )
            logger.info(f"CONNECT: {discord.version_info}")
            logger.info(f"CONNECT: Latency: {self.latency * 1000} ms")
            self.connected = True

        await self.sync_commands()
        logger.info("CONNECT: Commands synced")

    async def post_changelog_to_guild(self, discord_guild: discord.Guild) -> None:
        """Post the changelog to the specified guild.

        This function fetches the changelog channel for the guild and posts the changelog if there are any updates since the last posted version. It also updates the last posted version in the guild settings.

        Args:
            discord_guild (discord.Guild): The guild to post the changelog to.

        """
        guild = await Guild.find_one(Guild.id == discord_guild.id)

        # Don't post if there's no changelog channel
        changelog_channel = guild.fetch_changelog_channel(discord_guild)
        if not changelog_channel:
            logger.debug(f"CHANGELOG: No changelog channel found for {guild.name}")
            return

        # Find the most recent version
        global_properties = await GlobalProperty.find_one()
        server_version = global_properties.most_recent_version()

        # if no changelog has been posted, only post the most recent version
        if not guild.changelog_posted_version:
            guild.changelog_posted_version = global_properties.versions[-2]

        # Check if there are any updates to post
        if semver.compare(guild.changelog_posted_version, server_version) == 0:
            logger.debug(f"CHANGELOG: No updates to send to {guild.name}")
            return

        # Add 1 to the last posted version to get the next version to post
        version_to_post = server_version
        for v in ChangelogParser(self).list_of_versions():
            if v == guild.changelog_posted_version:
                break
            version_to_post = v

        # Initialize the changelog parser
        changelog = ChangelogParser(
            self,
            version_to_post,
            server_version,
            exclude_categories=[
                "docs",
                "refactor",
                "style",
                "test",
                "chore",
                "perf",
                "ci",
                "build",
            ],
        )
        if not changelog.has_updates():
            logger.debug(f"CHANGELOG: No updates to send to {guild.name}")
            return

        # Send the changelog embed to the channel
        embed = changelog.get_embed_personality()
        await changelog_channel.send(embed=embed)
        logger.debug(f"CHANGELOG: Post changelog to {guild.name}")

        # Update the guild's last posted version
        guild.changelog_posted_version = server_version
        await guild.save()

    async def _provision_guild(self, guild: discord.Guild) -> None:
        """Provision a guild on connect."""
        logger.info(f"CONNECT: Provision {guild.name} ({guild.id})")

        # Add/Update the guild in the database
        logger.debug(f"DATABASE: Update guild `{guild.name}`")
        guild_object = await Guild.find_one(Guild.id == guild.id).upsert(
            Set(
                {
                    "date_modified": datetime.now(timezone.utc).replace(microsecond=0),
                    "name": guild.name,
                }
            ),
            on_insert=Guild(id=guild.id, name=guild.name),
            response_type=UpdateResponse.NEW_DOCUMENT,
        )

        # Add/Update the users in the database
        for member in guild.members:
            if not member.bot:
                logger.debug(f"DATABASE: Update user `{member.name}`")
                user = await User.find_one(User.id == member.id).upsert(
                    Set(
                        {
                            "date_modified": datetime.now(timezone.utc).replace(microsecond=0),
                            "name": member.display_name,
                        }
                    ),
                    on_insert=User(id=member.id, name=member.display_name),
                    response_type=UpdateResponse.NEW_DOCUMENT,
                )
                if guild.id not in user.guilds:
                    user.guilds.append(guild.id)
                    await user.save()

        # Setup the necessary roles in the guild
        await guild_object.setup_roles(guild)

        # Post the changelog
        await self.post_changelog_to_guild(guild)

        logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")

    async def on_ready(self) -> None:
        """Override on_ready."""
        await self.wait_until_ready()

        # Needed for computing uptime
        self.start_time = datetime.utcnow()

        if not self.welcomed:
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            # Work with connected guilds
            for guild in self.guilds:
                await self._provision_guild(guild)

        self.welcomed = True
        logger.info(f"{self.user} is ready")

    # Define a custom application context class
    async def get_application_context(  # type: ignore
        self, interaction: discord.Interaction, cls=ValentinaContext  # noqa: PLR6301
    ) -> discord.ApplicationContext:
        """Override the get_application_context method to use my custom context."""
        return await super().get_application_context(interaction, cls=cls)
