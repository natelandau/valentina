"""The main file for the Valentina bot."""

from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

import discord
from aiohttp import ClientSession
from discord.ext import commands, tasks
from loguru import logger

from valentina.models import (
    CharacterService,
    ChronicleService,
    DatabaseService,
    GuildService,
    MacroService,
    TraitService,
    UserService,
)
from valentina.models.db_tables import DATABASE, Guild
from valentina.models.errors import reporter
from valentina.utils import Context


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
        self.macro_svc = MacroService()

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

        # Allow computing uptime
        self.start_time = datetime.utcnow()

        if not self.welcomed:
            # Start tasks
            # #######################
            backup_db.start(self.db_svc, self.config)
            logger.info("BOT: Start background database backup task")

            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="for /help")
            )

            # Setup Guilds
            # #######################

            for guild in self.guilds:
                # Create Storyteller role
                # ############################
                storyteller = discord.utils.get(guild.roles, name="Storyteller")

                if storyteller is None:
                    storyteller = await guild.create_role(
                        name="Storyteller",
                        color=discord.Color.dark_teal(),
                        mentionable=True,
                        hoist=True,
                    )

                perms = discord.Permissions()
                perms.update(
                    add_reactions=True,
                    attach_files=True,
                    can_create_instant_invite=True,
                    change_nickname=True,
                    connect=True,
                    create_private_threads=True,
                    create_public_threads=True,
                    embed_links=True,
                    external_emojis=True,
                    external_stickers=True,
                    manage_messages=True,
                    manage_threads=True,
                    mention_everyone=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages_in_threads=True,
                    send_messages=True,
                    send_tts_messages=True,
                    speak=True,
                    stream=True,
                    use_application_commands=True,
                    use_external_emojis=True,
                    use_external_stickers=True,
                    use_slash_commands=True,
                    use_voice_activation=True,
                    view_channel=True,
                )
                await storyteller.edit(reason=None, permissions=perms)
                logger.debug(f"CONNECT: {storyteller.name} role created")

                # Create Player role
                # ############################
                player = discord.utils.get(guild.roles, name="Player", mentionable=True, hoist=True)

                if player is None:
                    player = await guild.create_role(
                        name="Player",
                        color=discord.Color.dark_blue(),
                        mentionable=True,
                        hoist=True,
                    )

                perms = discord.Permissions()
                perms.update(
                    add_reactions=True,
                    attach_files=True,
                    can_create_instant_invite=True,
                    change_nickname=True,
                    connect=True,
                    create_private_threads=True,
                    create_public_threads=True,
                    embed_links=True,
                    external_emojis=True,
                    external_stickers=True,
                    mention_everyone=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages_in_threads=True,
                    send_messages=True,
                    send_tts_messages=True,
                    speak=True,
                    stream=True,
                    use_application_commands=True,
                    use_external_emojis=True,
                    use_external_stickers=True,
                    use_slash_commands=True,
                    use_voice_activation=True,
                    view_channel=True,
                )
                await player.edit(reason=None, permissions=perms)
                logger.debug(f"CONNECT: {player.name} role created")

                positions = {
                    guild.default_role: 0,
                    player: 1,
                    storyteller: 2,
                }  # penultimate role

                await guild.edit_role_positions(positions=positions)  # type: ignore [arg-type]

                # Add guild to database
                # ############################

                self.guild_svc.update_or_add(guild)
                logger.info(f"CONNECT: Playing on {guild.name} ({guild.id})")

            # Update all character default values in case something changed
            self.char_svc.set_character_default_values()

        self.welcomed = True
        logger.info(f"{self.user} is ready")

    async def on_message(self, message: discord.Message) -> None:
        """If the message is a reply to an RP post, ping the RP post's author."""
        if message.author.bot:
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

    @staticmethod
    async def on_application_command_error(
        ctx: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        """Use centralized reporter to handle errors."""
        await reporter.report_error(ctx, error)

    @staticmethod
    async def on_guild_update(before: discord.Guild, after: discord.Guild) -> None:
        """Log guild name changes and update the database."""
        if before.name != after.name:
            logger.info(f"BOT: Rename guild `{before.name}` => `{after.name}`")
            Guild.update(name=after.name).where(Guild.id == after.id).execute()


@tasks.loop(time=time(0, tzinfo=timezone.utc))
async def backup_db(db_svc: DatabaseService, config: dict) -> None:
    """Backup the database."""
    logger.info("BOT: Run background database backup task")
    await db_svc.backup_database(config)
