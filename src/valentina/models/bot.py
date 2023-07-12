"""The main file for the Valentina bot."""

from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

import discord
from aiohttp import ClientSession
from discord.ext import commands, tasks
from loguru import logger

from valentina.models.database import DATABASE
from valentina.models.database_services import (
    CharacterService,
    ChronicleService,
    DatabaseService,
    GuildService,
    TraitService,
    UserService,
)
from valentina.utils import Context, DBBackup


class Valentina(commands.Bot):
    """Subclass discord.Bot."""

    def __init__(self, parent_dir: Path, config: dict, version: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.char_service: Any = None
        self.parent_dir = parent_dir
        self.config = config
        self.version = version
        self.owner_channels = [int(x) for x in self.config["VALENTINA_OWNER_CHANNELS"].split(",")]

        # Create in-memory caches
        self.db_svc = DatabaseService(DATABASE)
        self.guild_svc = GuildService()
        self.char_svc = CharacterService()
        self.chron_svc = ChronicleService()
        self.trait_svc = TraitService()
        self.user_svc = UserService()

        logger.info("BOT: Running setup tasks")
        for cog in Path(self.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                logger.info(f"COGS: Loading - {cog.stem}")
                self.load_extension(f"valentina.cogs.{cog.stem}")

        logger.info("BOT: Setup tasks complete")

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

        # Allow computing uptime
        self.start_time = datetime.utcnow()

        if not self.welcomed:
            # Start tasks
            # #######################
            backup_db.start(self.config)
            logger.debug("BOT: Start background database backup task")

            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            # Setup database
            # #######################
            self.db_svc.create_tables()

            if self.db_svc.requires_migration(self.version):
                self.db_svc.migrate_old_database(self.version)

            self.db_svc.sync_enums()

            # Setup Guilds
            # #######################

            for guild in self.guilds:
                logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")
                self.guild_svc.update_or_add(guild)
                self.char_svc.fetch_all_characters(guild.id)

        logger.info("BOT: In-memory caches created")

        self.welcomed = True
        logger.info(f"{self.user} is ready")

    async def on_message(self, message: discord.Message) -> None:
        """If the message is a reply to an RP post, ping the RP post's author."""
        if message.author.bot:
            logger.debug("BOT: Disregarding bot message")
            return

        # This line allows using prefixed commands
        if message.channel.id in self.owner_channels:
            await self.process_commands(message)

    async def get_application_context(self, interaction: discord.Interaction) -> Context:  # type: ignore [override]
        """Return a custom application context."""
        return Context(self, interaction)

    @property
    def http_session(self) -> ClientSession:
        """Return the aiohttp session."""
        return self.http._HTTPClient__session  # type: ignore # it exists, I promise


@tasks.loop(time=time(0, tzinfo=timezone.utc))
async def backup_db(config: dict) -> None:
    """Backup the database."""
    await DBBackup(config).create_backup()
    await DBBackup(config).clean_old_backups()
