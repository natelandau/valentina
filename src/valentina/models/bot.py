"""The main file for the Valentina bot."""

import asyncio
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import arrow
import discord
import pymongo
import semver
from beanie import UpdateResponse
from beanie.operators import Set
from discord.ext import commands
from loguru import logger

from valentina.constants import (
    ChannelPermission,
    EmbedColor,
    LogLevel,
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
)
from valentina.models import (
    Campaign,
    ChangelogPoster,
    Character,
    GlobalProperty,
    Guild,
    User,
)
from valentina.utils import ValentinaConfig, errors
from valentina.utils.database import init_database
from valentina.utils.discord_utils import set_channel_perms


# Subclass discord.ApplicationContext to create custom application context
class ValentinaContext(discord.ApplicationContext):
    """A custom application context for Valentina."""

    def log_command(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:  # pragma: no cover
        """Log the command to the console and log file."""
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

    async def can_kill_character(self, character: Character) -> bool:
        """Check if the user can kill the character.

        Args:
            character (Character): The character to check.

        Returns:
            bool: True if the user can kill the character, False otherwise.
        """
        # Always allow administrators to kill characters
        if isinstance(self.author, discord.Member) and self.author.guild_permissions.administrator:
            return True

        # Grab the setting from the guild
        guild = await Guild.get(self.guild.id)
        try:
            setting = PermissionsKillCharacter(guild.permissions.kill_character)
        except KeyError:
            setting = PermissionsKillCharacter.CHARACTER_OWNER_ONLY

        if setting == PermissionsKillCharacter.UNRESTRICTED:
            return True

        if setting == PermissionsKillCharacter.CHARACTER_OWNER_ONLY and isinstance(
            self.author, discord.Member
        ):
            return self.author.id == character.user_owner or "Storyteller" in [
                x.name for x in self.author.roles
            ]

        if setting == PermissionsKillCharacter.STORYTELLER_ONLY and isinstance(
            self.author, discord.Member
        ):
            return "Storyteller" in [x.name for x in self.author.roles]

        return True

    async def can_manage_traits(self, character: Character) -> bool:
        """Check if the user can manage traits for the character.

        Args:
            character (Character): The character to check.

        Returns:
            bool: True if the user can manage traits for the character, False otherwise.
        """
        # Always allow administrators to manage traits
        if isinstance(self.author, discord.Member) and self.author.guild_permissions.administrator:
            return True

        # Grab the setting from the guild
        guild = await Guild.get(self.guild.id)
        try:
            setting = PermissionsManageTraits(guild.permissions.manage_traits)
        except KeyError:
            setting = PermissionsManageTraits.WITHIN_24_HOURS

            # Check permissions based on the setting
        if setting == PermissionsManageTraits.UNRESTRICTED:
            return True

        if setting == PermissionsManageTraits.CHARACTER_OWNER_ONLY and isinstance(
            self.author, discord.Member
        ):
            is_character_owner = self.author.id == character.user_owner
            is_storyteller = "Storyteller" in [role.name for role in self.author.roles]
            return is_character_owner or is_storyteller

        if setting == PermissionsManageTraits.WITHIN_24_HOURS and isinstance(
            self.author, discord.Member
        ):
            is_storyteller = "Storyteller" in [role.name for role in self.author.roles]
            is_character_owner = self.author.id == character.user_owner
            is_within_24_hours = arrow.utcnow() - arrow.get(character.created) <= timedelta(
                hours=24
            )
            return is_storyteller or (is_character_owner and is_within_24_hours)

        if setting == PermissionsManageTraits.STORYTELLER_ONLY and isinstance(
            self.author, discord.Member
        ):
            return "Storyteller" in [role.name for role in self.author.roles]

        return True

    async def can_grant_xp(self, user: User) -> bool:
        """Check if the user can grant xp to the user.

        Args:
            user (User): The user to check.

        Returns:
            bool: True if the user can grant xp to the user, False otherwise.
        """
        # Always allow administrators to manage traits
        if isinstance(self.author, discord.Member) and self.author.guild_permissions.administrator:
            return True

        # Grab the setting from the guild
        guild = await Guild.get(self.guild.id)
        try:
            setting = PermissionsGrantXP(guild.permissions.grant_xp)
        except KeyError:
            setting = PermissionsGrantXP.PLAYER_ONLY

            # Check permissions based on the setting
        if setting == PermissionsGrantXP.UNRESTRICTED:
            return True

        if isinstance(self.author, discord.Member) and setting == PermissionsGrantXP.PLAYER_ONLY:
            is_user = self.author.id == user.id
            is_storyteller = "Storyteller" in [role.name for role in self.author.roles]
            return is_user or is_storyteller

        if (
            isinstance(self.author, discord.Member)
            and setting == PermissionsGrantXP.STORYTELLER_ONLY
        ):
            return "Storyteller" in [role.name for role in self.author.roles]

        return True

    async def can_manage_campaign(self) -> bool:
        """Check if the user can manage the campaign.

        Returns:
            bool: True if the user can manage the campaign, False otherwise.
        """
        # Always allow administrators to manage traits
        if isinstance(self.author, discord.Member) and self.author.guild_permissions.administrator:
            return True

        # Grab the setting from the guild
        guild = await Guild.get(self.guild.id)
        try:
            setting = PermissionManageCampaign(guild.permissions.manage_campaign)
        except KeyError:
            setting = PermissionManageCampaign.STORYTELLER_ONLY

        # Check permissions based on the setting
        if setting == PermissionManageCampaign.UNRESTRICTED:
            return True

        if (
            isinstance(self.author, discord.Member)
            and setting == PermissionManageCampaign.STORYTELLER_ONLY
        ):
            return "Storyteller" in [role.name for role in self.author.roles]

        return True

    async def channel_update_or_add(
        self,
        channel: str | discord.TextChannel,
        topic: str,
        permissions: tuple[ChannelPermission, ChannelPermission, ChannelPermission],
    ) -> discord.TextChannel:  # pragma: no cover
        """Create or update a channel in the guild.

        Either create a new text channel in the guild or update an existing onebased on the name. Set permissions for default role, player role, and storyteller role. If a member is a bot, set permissions to manage.

        Args:
            channel (str|discord.TextChannel): Channel name or object.
            topic (str): Channel topic.
            permissions (tuple[ChannelPermission, ChannelPermission, ChannelPermission]): Tuple containing channel permissions for default_role, player_role, storyteller_role.

        Returns:
            discord.TextChannel: The created or updated text channel.
        """
        # Fetch roles
        player_role = discord.utils.get(self.guild.roles, name="Player")
        storyteller_role = discord.utils.get(self.guild.roles, name="Storyteller")

        # Initialize permission overwrites
        overwrites = {
            self.guild.default_role: set_channel_perms(permissions[0]),
            player_role: set_channel_perms(permissions[1]),
            storyteller_role: set_channel_perms(permissions[2]),
            **{
                user: set_channel_perms(ChannelPermission.MANAGE)
                for user in self.guild.members
                if user.bot
            },
        }

        # Determine channel object and name
        if isinstance(channel, discord.TextChannel):
            channel_object = channel
        elif isinstance(channel, str):
            channel_name = channel.lower().strip()
            channel_object = discord.utils.get(self.guild.text_channels, name=channel_name)

            # Create the channel if it doesn't exist
            if not channel_object:
                logger.debug(
                    f"GUILD: Create channel '{channel_object.name}' on '{self.guild.name}'"
                )
                return await self.guild.create_text_channel(
                    channel_name,
                    overwrites=overwrites,
                    topic=topic,
                )

        # Update existing channel
        logger.debug(f"GUILD: Update channel '{channel_object.name}' on '{self.guild.name}'")
        await channel_object.edit(overwrites=overwrites, topic=topic)

        return channel_object

    async def fetch_active_character(self, raise_error: bool = True) -> Character | None:
        """Fetch the active character for the user.

        Args:
            raise_error (bool, optional): Whether to raise an error if no active character is found. Defaults to True. Returns None if False.

        Returns:
            Character | None: The active character for the user or None if no active character is found.
        """
        user = await User.get(self.author.id, fetch_links=True)
        return await user.active_character(self.guild, raise_error=raise_error)

    async def fetch_active_campaign(self, raise_error: bool = True) -> Campaign:
        """Fetch the active campaign for the user.

        Args:
            raise_error (bool, optional): Whether to raise an error if no active campaign is found. Defaults to True. Returns None if False.

        Returns:
            Campaign: The active campaign for the user.
        """
        guild = await Guild.get(self.guild.id, fetch_links=True)
        campaign = guild.active_campaign
        if not campaign and raise_error:
            raise errors.NoActiveCampaignError

        return campaign


class Valentina(commands.Bot):
    """Subclass discord.Bot."""

    def __init__(self, parent_dir: Path, version: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.parent_dir = parent_dir
        self.version = version
        self.owner_channels = [int(x) for x in ValentinaConfig().owner_channels.split(",")]

        # Load Cogs
        # #######################
        for cog in Path(self.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                logger.info(f"COGS: Loading - {cog.stem}")
                self.load_extension(f"valentina.cogs.{cog.stem}")

        logger.debug(f"COGS: Loaded {len(self.cogs)} cogs")

    async def on_connect(self) -> None:
        """Perform early setup."""
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
        """Update the changelog."""
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
        """Provision a guild on connect."""
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

        logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")

    async def on_ready(self) -> None:
        """Override on_ready. Additional functionality is in the on_ready listener in event_listener.py."""
        await self.wait_until_ready()
        while not self.connected:
            logger.warning("CONNECT: Waiting for connection...")
            await asyncio.sleep(10)

        # Needed for computing uptime
        self.start_time = datetime.utcnow()

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

    # Define a custom application context class
    async def get_application_context(  # type: ignore
        self, interaction: discord.Interaction, cls=ValentinaContext
    ) -> discord.ApplicationContext:
        """Override the get_application_context method to use my custom context."""
        return await super().get_application_context(interaction, cls=cls)
