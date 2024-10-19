"""The main file for the Valentina bot."""

import asyncio
import inspect
from datetime import UTC, datetime
from typing import Any

import discord
import pymongo
import semver
from beanie import UpdateResponse
from beanie.operators import Set
from discord.ext import commands, tasks
from loguru import logger

from valentina.constants import (
    COGS_PATH,
    EmbedColor,
    LogLevel,
)
from valentina.discord.models import SyncDiscordFromWebManager
from valentina.models import (
    Campaign,
    ChangelogPoster,
    GlobalProperty,
    Guild,
    User,
)
from valentina.utils import ValentinaConfig, errors
from valentina.utils.database import init_database


# Subclass discord.ApplicationContext to create custom application context
class ValentinaContext(discord.ApplicationContext):
    """Extend discord.ApplicationContext with Valentina-specific functionality.

    Provide custom methods and properties for handling Valentina's command context.
    Implement logging capabilities and embed creation for consistent message formatting.
    """

    def log_command(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:  # pragma: no cover
        """Log the executed command with contextual information.

        Log the command details to both console and log file, including the author,
        command name, and channel where it was executed. Determine the appropriate
        log level and construct a detailed log message with the command's context.
        Use introspection to identify the calling function and create a hierarchical
        logger name for better traceability.
        """
        author = f"@{self.author.display_name}" if hasattr(self, "author") else None
        command = f"'/{self.command.qualified_name}'" if hasattr(self, "command") else None
        channel = f"#{self.channel.name}" if hasattr(self, "channel") else None

        command_info = [author, command, channel]

        if (
            inspect.stack()[1].function == "post_to_audit_log"
            and inspect.stack()[2].function == "confirm_action"
        ):
            name1 = inspect.stack()[3].filename.split("/")[-3].split(".")[0]
            name2 = inspect.stack()[3].filename.split("/")[-2].split(".")[0]
            name3 = inspect.stack()[3].filename.split("/")[-1].split(".")[0]
            new_name = f"{name1}.{name2}.{name3}"
        elif inspect.stack()[1].function == "post_to_audit_log":
            name1 = inspect.stack()[2].filename.split("/")[-3].split(".")[0]
            name2 = inspect.stack()[2].filename.split("/")[-2].split(".")[0]
            name3 = inspect.stack()[2].filename.split("/")[-1].split(".")[0]
            new_name = f"{name1}.{name2}.{name3}"
        else:
            name1 = inspect.stack()[1].filename.split("/")[-3].split(".")[0]
            name2 = inspect.stack()[1].filename.split("/")[-2].split(".")[0]
            name3 = inspect.stack()[1].filename.split("/")[-1].split(".")[0]
            new_name = f"{name1}.{name2}.{name3}"

        logger.patch(lambda r: r.update(name=new_name)).log(  # type: ignore [call-arg]
            level.value, f"{msg} [{', '.join([x for x in command_info if x])}]"
        )

    def _message_to_embed(self, message: str) -> discord.Embed:  # pragma: no cover
        """Convert a string message to a Discord embed.

        Create a Discord embed object from the given message string. Set the embed's
        color based on the command category, add a timestamp, and include footer
        information about the command, user, and channel. The embed's title is set
        to the input message.

        Args:
            message (str): The message to be used as the embed's title.

        Returns:
            discord.Embed: A fully formatted Discord embed object.
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
        """Post an error message or embed to the guild's error log channel.

        Convert the input message to an embed if it's a string. Attempt to send the
        error information to the guild's designated error log channel. If the message
        is too long, send a truncated version with basic error details.

        Args:
            message (str | discord.Embed): The error message or embed to send.
            error (Exception): The exception that triggered the error log.

        Raises:
            discord.DiscordException: If the error message cannot be sent to the channel.
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
        """Send a message to the guild's audit log channel.

        Convert the input message to an embed if it's a string, otherwise send the provided embed. Log the message content to the command log. Attempt to send the message to the guild's designated audit log channel.

        Args:
            message (str | discord.Embed): The message or embed to send to the audit log.

        Raises:
            errors.MessageTooLongError: If the message exceeds Discord's character limit.
        """
        # Get the database guild object and error log channel
        guild = await Guild.get(self.guild.id)
        audit_log_channel = guild.fetch_audit_log_channel(self.guild)

        if isinstance(message, str):
            self.log_command(message, LogLevel.INFO)

        if isinstance(message, discord.Embed):
            self.log_command(f"{message.title} {message.description}", LogLevel.INFO)

        if audit_log_channel:
            embed = self._message_to_embed(message) if isinstance(message, str) else message

            try:
                await audit_log_channel.send(embed=embed)
            except discord.HTTPException as e:
                raise errors.MessageTooLongError from e


class Valentina(commands.Bot):
    """Extend the discord.Bot class to create a custom bot implementation.

    Enhance the base discord.Bot with additional functionality
    specific to the Valentina bot. Include custom attributes, methods,
    and event handlers to manage bot state, load cogs, initialize the database,
    and handle server connections.
    """

    def __init__(self, version: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.version = version
        self.owner_channels = [int(x) for x in ValentinaConfig().owner_channels.split(",")]
        self.sync_from_web.start()
        self.sync_roles_to_db.start()

        # Load Cogs
        # #######################
        for cog in COGS_PATH.glob("*.py"):
            if cog.stem[0] != "_":
                logger.info(f"COGS: Loading - {cog.stem}")
                self.load_extension(f"valentina.discord.cogs.{cog.stem}")

        logger.debug(f"COGS: Loaded {len(self.cogs)} cogs")

    async def on_connect(self) -> None:
        """Perform early setup tasks when the bot connects to Discord.

        Initialize the MongoDB database connection, retrying if necessary.
        Log connection details and bot information upon successful connection.
        Synchronize commands with Discord.
        """
        # Initialize the mongodb database
        while True:
            try:
                await init_database()
            except pymongo.errors.ServerSelectionTimeoutError as e:
                logger.error(f"DB: Failed to initialize database: {e}")
                await asyncio.sleep(60)
            else:
                break

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

    async def post_changelog_to_guild(self, guild: discord.Guild) -> None:
        """Post the latest changelog updates to the specified guild.

        Retrieve the most recent version from global properties and compare it with the
        guild's last posted changelog version. If updates are available, fetch the
        changelog, post it to the designated channel, and update the guild's changelog
        version in the database. Handle potential errors during the process and log
        relevant information.
        """
        db_global_properties = await GlobalProperty.find_one()

        # Post Changelog to the #changelog channel, if set
        db_guild = await Guild.find_one(Guild.id == guild.id)
        if not db_guild:
            logger.error(f"DATABASE: Could not find guild {guild.name} ({guild.id})")
            return

        # Check if there are any updates to post
        if (
            db_guild.changelog_posted_version
            and semver.compare(
                db_guild.changelog_posted_version, db_global_properties.most_recent_version
            )
            == 0
        ):
            logger.debug(f"CHANGELOG: No updates to send to {db_guild.name}")
            return

        # Grab the changelog
        try:
            changelog = ChangelogPoster(
                bot=self,
                channel=db_guild.fetch_changelog_channel(guild),
                oldest_version=db_guild.changelog_posted_version,
                newest_version=db_global_properties.most_recent_version,
                with_personality=True,
                exclude_oldest_version=True,
            )
        except errors.VersionNotFoundError:
            logger.error(f"CHANGELOG: Could not find version {self.version} in the changelog")
            return

        await changelog.post()
        logger.info(f"CHANGELOG: Posted changelog to {db_guild.name}")

        # Update the changelog version for the guild
        db_guild.changelog_posted_version = db_global_properties.most_recent_version
        await db_guild.save()
        logger.debug(f"DATABASE: Update guild `{db_guild.name}` with v{self.version}")

    @staticmethod
    async def _provision_guild(guild: discord.Guild) -> None:
        """Provision a guild upon connection to Discord.

        Set up the necessary database entries, roles, and configurations for a newly
        connected guild. Update existing guild information if already present. Process
        guild members, ensuring their information is current in the database. Perform
        any required data migrations or updates for existing campaigns.
        """
        logger.info(f"CONNECT: Provision {guild.name} ({guild.id})")

        # Add/Update the guild in the database
        guild_object = await Guild.find_one(Guild.id == guild.id).upsert(
            Set(
                {
                    "date_modified": datetime.now(UTC).replace(microsecond=0),
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
                            "date_modified": datetime.now(UTC).replace(microsecond=0),
                            "name": member.display_name,
                            "avatar_url": str(member.display_avatar.url),
                        }
                    ),
                    on_insert=User(
                        id=member.id,
                        name=member.display_name,
                        avatar_url=str(member.display_avatar.url),
                    ),
                    response_type=UpdateResponse.NEW_DOCUMENT,
                )
                if guild.id not in user.guilds:
                    user.guilds.append(guild.id)
                    await user.save()

        # Add `is_deleted` to campaigns
        # TODO: Remove this after migration
        for campaign in await Campaign.find(Campaign.guild == guild.id).to_list():
            if not campaign.is_deleted:
                campaign.is_deleted = False
                await campaign.save()
                logger.info(
                    f"DATABASE: Add `is_deleted` to campaign {campaign.name} ({campaign.id})"
                )

        # Setup the necessary roles in the guild
        await guild_object.setup_roles(guild)

        logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")

    async def on_ready(self) -> None:
        """Override the on_ready method to initialize essential bot tasks.

        Perform core setup operations when the bot becomes ready. Wait for full
        connection, set the bot's presence, initialize the database, and provision
        connected guilds. Set the start time for uptime calculations and manage
        version tracking in the database. Initiate the web server if enabled in
        the configuration.

        Additional functionality is implemented in the on_ready listener within
        event_listener.py.
        """
        await self.wait_until_ready()
        while not self.connected:
            logger.warning("CONNECT: Waiting for connection...")
            await asyncio.sleep(10)

        # Needed for computing uptime
        self.start_time = datetime.now(UTC)

        if not self.welcomed:
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            if not await GlobalProperty.find_one():
                logger.info("DATABASE: Create GlobalProperty")
                await GlobalProperty().save()

            db_global_properties = await GlobalProperty.find_one()

            # Grab current bot version
            latest_db_version = db_global_properties.most_recent_version
            logger.debug(f"DATABASE: Current version: {latest_db_version}")

            # Add updated bot version to the database
            if self.version not in db_global_properties.versions:
                logger.info(f"DATABASE: Add version {self.version} to GlobalProperty")
                db_global_properties.versions.append(self.version)
                await db_global_properties.save()

            # Work with connected guilds
            for guild in self.guilds:
                await self._provision_guild(guild)
                await self.post_changelog_to_guild(guild)

        self.welcomed = True
        logger.info(f"{self.user} is ready")

        if ValentinaConfig().webui_enable:
            from valentina.webui import run_webserver

            await run_webserver()

    # Define a custom application context class
    async def get_application_context(  # type: ignore
        self, interaction: discord.Interaction, cls=ValentinaContext
    ) -> discord.ApplicationContext:
        """Override the get_application_context method to use a custom context.

        Return a ValentinaContext instance instead of the default ApplicationContext.
        This allows for custom functionality and attributes specific to the Valentina
        bot to be available in all command interactions.

        Args:
            interaction (discord.Interaction): The interaction object from Discord.
            cls (Type[ValentinaContext], optional): The context class to use. Defaults to ValentinaContext.

        Returns:
            ValentinaContext: A custom application context for Valentina bot interactions.
        """
        return await super().get_application_context(interaction, cls=cls)

    @tasks.loop(minutes=5)
    async def sync_from_web(self) -> None:
        """Some changes made via the Webui are not automatically synced to Discord. For example, characters created on the web will not have their channels created on Discord. This task will periodically check for changes from the WebUI and sync them to Discord or vice-a-versa."""
        logger.debug("SYNC: Running sync_from_web task")
        sync_discord = SyncDiscordFromWebManager(self)
        await sync_discord.run()

    @sync_from_web.before_loop
    async def before_sync_from_web(self) -> None:
        """Wait for the bot to be ready before starting the sync_from_web task."""
        await self.wait_until_ready()

    @tasks.loop(minutes=10)
    async def sync_roles_to_db(self) -> None:
        """This task keeps guild-user role lists in sync with changes made to user roles using the Discord interface."""
        logger.info("SYNC: Running sync_roles_to_db task")
        for guild in self.guilds:
            guild_db_obj = await Guild.get(guild.id)
            for member in [x for x in guild.members if not x.bot]:
                if (
                    member.guild_permissions.administrator
                    and member.id not in guild_db_obj.administrators
                ):
                    guild_db_obj.administrators.append(member.id)
                    await guild_db_obj.save()
                    logger.info(f"PERMS: Add {member.name} as administrator in database")

                if (
                    not member.guild_permissions.administrator
                    and member.id in guild_db_obj.administrators
                ):
                    guild_db_obj.administrators.remove(member.id)
                    await guild_db_obj.save()
                    logger.info(f"PERMS: Remove {member.name} as administrator in database")

                if (
                    any(role.name in ("Storyteller", "@Storyteller") for role in member.roles)
                    and member.id not in guild_db_obj.storytellers
                ):
                    guild_db_obj.storytellers.append(member.id)
                    await guild_db_obj.save()
                    logger.info(f"PERMS: Add {member.name} as @Storyteller in database")

                if (
                    not any(role.name in ("Storyteller", "@Storyteller") for role in member.roles)
                    and member.id in guild_db_obj.storytellers
                ):
                    guild_db_obj.storytellers.remove(member.id)
                    await guild_db_obj.save()
                    logger.info(f"PERMS: Remove {member.name} as @Storyteller in database")

    @sync_roles_to_db.before_loop
    async def before_sync_roles_to_db(self) -> None:
        """Wait for the bot to be ready before starting the sync_from_web task."""
        await self.wait_until_ready()