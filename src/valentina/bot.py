"""The main file for the Valentina bot."""

from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

import discord
from aiohttp import ClientSession
from discord.ext import commands, tasks
from loguru import logger

from valentina.__version__ import __version__
from valentina.utils.context import Context


class Valentina(commands.Bot):
    """Subclass discord.Bot."""

    def __init__(self, parent_dir: Path, config: dict, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.char_service: Any = None
        self.parent_dir = parent_dir
        self.config = config

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
            from valentina import DATABASE, char_svc, guild_svc
            from valentina.models.database_services import DatabaseService

            # Database setup
            DatabaseService(DATABASE).create_tables()

            if DatabaseService(DATABASE).requires_migration(__version__):
                DatabaseService(DATABASE).migrate_old_database(__version__)

            DatabaseService(DATABASE).sync_enums()

            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            for guild in self.guilds:
                guild_svc.update_or_add(guild)
                char_svc.fetch_all_characters(guild.id)
                await guild.system_channel.send(
                    ":wave: Beware, I have connected to this server. I will be watching you."
                )

            # Start tasks
            # #######################
            backup_db.start(self.config)

            logger.info("BOT: Internal cache built")
            self.welcomed = True

        logger.info("BOT: Ready")

    async def on_message(self, message: discord.Message) -> None:
        """If the message is a reply to an RP post, ping the RP post's author."""
        if message.author.bot:
            logger.debug("BOT: Disregarding bot message")
            return
        if message.type != discord.MessageType.reply:
            logger.debug("BOT: Disregarding non-reply message.")
            return
        if message.reference is None:
            logger.debug("BOT: Disregarding message with no reference.")
            return

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
    from .backup_db import DBBackup

    await DBBackup(config).create_backup()
    await DBBackup(config).clean_old_backups()
