"""The main file for the Valentina bot."""

from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands, tasks
from loguru import logger

from valentina.models import (
    AWSService,
    CampaignService,
    CharacterService,
    DatabaseService,
    GuildService,
    MacroService,
    TraitService,
    UserService,
)
from valentina.models.db_tables import DATABASE


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

        # Create in-memory caches
        self.db_svc = DatabaseService(DATABASE)
        self.guild_svc = GuildService(bot=self)
        self.char_svc = CharacterService()
        self.campaign_svc = CampaignService()
        self.trait_svc = TraitService()
        self.user_svc = UserService(bot=self)
        self.macro_svc = MacroService()
        self.aws_svc = AWSService(
            aws_access_key_id=self.config.get("VALENTINA_AWS_ACCESS_KEY_ID", False),
            aws_secret_access_key=self.config.get("VALENTINA_AWS_SECRET_ACCESS_KEY", False),
            bucket_name=self.config.get("VALENTINA_S3_BUCKET_NAME", False),
        )

        # Load Cogs
        # #######################
        for cog in Path(self.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                logger.info(f"COGS: Loading - {cog.stem}")
                self.load_extension(f"valentina.cogs.{cog.stem}")

    async def on_connect(self) -> None:
        """Perform early setup."""
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

    async def on_ready(self) -> None:
        """Override on_ready."""
        await self.wait_until_ready()

        # Needed for computing uptime
        self.start_time = datetime.utcnow()

        if not self.welcomed:
            # Start tasks
            # #######################
            backup_db.start(self.db_svc, self.config)
            logger.info("BOT: Start background database backup task")

            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            logger.debug(f"Connected Guilds: {self.guilds=}")

            for guild in self.guilds:
                logger.info(f"CONNECT: Provision {guild.name} ({guild.id})")

                # Add guild to database
                logger.debug("CONNECT: Update guild in database")
                self.guild_svc.update_or_add(guild=guild)

                # Update all existing users in the guild
                await self.guild_svc.update_guild_users(guild=guild)

                # Send welcome message
                await self.guild_svc.post_changelog(guild=guild, bot=self)

                logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")

            # Update all character default values in case something changed
            self.char_svc.set_character_default_values()

        self.welcomed = True
        logger.info(f"{self.user} is ready")


@tasks.loop(time=time(8, tzinfo=timezone.utc))
async def backup_db(db_svc: DatabaseService, config: dict) -> None:
    """Run a periodic backup of the database.

    This function is scheduled to run as a background task at a fixed time every day.

    Args:
        db_svc (DatabaseService): An instance of the DatabaseService class, responsible for performing the actual backup.
        config (dict): Configuration settings for the backup operation.
    """
    logger.info("BOT: Run background database backup task")
    await db_svc.backup_database(config)
