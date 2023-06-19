"""The main file for the Valentina bot."""

from pathlib import Path
from typing import Any

import discord
from discord.ext import commands
from loguru import logger


class Valentina(commands.Bot):
    """Subclass discord.Bot."""

    def __init__(self, parent_dir: Path, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.welcomed = False
        self.char_service: Any = None
        self.parent_dir = parent_dir

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
        if not self.welcomed:
            from valentina import DATABASE, char_svc
            from valentina.models.database_services import DatabaseService, GuildService

            # Database setup
            if not Path(DATABASE.database).exists():
                DatabaseService(DATABASE).create_new_db()
            else:
                DatabaseService(DATABASE).requires_migration()

            for _guild in self.guilds:
                GuildService.update_or_add(guild_id=_guild.id, guild_name=_guild.name)
                char_svc.fetch_all_characters(_guild.id)

            # TODO: Setup tasks here  User.set_by_id(3, {'is_admin': True})

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
