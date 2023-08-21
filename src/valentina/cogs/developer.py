# mypy: disable-error-code="valid-type"
"""Commands for bot development."""
from datetime import datetime
from pathlib import Path
from random import randrange

import aiofiles
import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from loguru import logger
from peewee import fn

from valentina.constants import MAX_CHARACTER_COUNT, EmbedColor
from valentina.models.bot import Valentina
from valentina.models.db_tables import Character, CharacterClass, RollProbability, VampireClan
from valentina.utils.converters import ValidCharacterClass
from valentina.utils.helpers import fetch_random_name
from valentina.utils.options import select_char_class
from valentina.views import ConfirmCancelButtons, present_embed

p = inflect.engine()


class Developer(commands.Cog):
    """Valentina developer commands. Beware, these can be destructive."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    ### BOT ADMINISTRATION COMMANDS ################################################################

    developer = discord.SlashCommandGroup(
        "developer",
        "Valentina developer commands. Beware, these can be destructive.",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @developer.command()
    @commands.is_owner()
    @logger.catch
    async def backupdb(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a backup of the database."""
        logger.info("ADMIN: Manually create database backup")
        db_file = await self.bot.db_svc.backup_database(self.bot.config)
        await present_embed(
            ctx,
            title="Database backup created",
            description=f"`{db_file}`",
            ephemeral=hidden,
            level="success",
        )

    @developer.command(description="Clear probability data from the database")
    @commands.is_owner()
    async def clear_probability_data(self, ctx: discord.ApplicationContext) -> None:
        """Clear probability data from the database."""
        cached_results = RollProbability.select()

        for result in cached_results:
            result.delete_instance()

        logger.info(f"DEVELOPER: {ctx.author.display_name} cleared probability data from the db")
        await present_embed(
            ctx,
            title="Probability data cleared",
            description=f"Cleared {len(cached_results)} probability results cleared from the database",
            ephemeral=True,
            level="success",
        )

    @developer.command()
    @commands.guild_only()
    @commands.is_owner()
    async def create_test_characters(
        self,
        ctx: discord.ApplicationContext,
        number: Option(
            int, description="The number of characters to create (default 1)", default=1
        ),
        char_class: Option(
            ValidCharacterClass,
            name="char_class",
            description="The character's class",
            autocomplete=select_char_class,
            required=False,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create test characters in the database for the current guild."""
        # Ensure the user is in the database
        self.bot.user_svc.fetch_user(ctx)

        for _ in range(number):
            # Assign a random class unless specified
            if char_class is None:
                char_class = CharacterClass.select().order_by(fn.Random()).limit(1).get()

            # Assign a random vampire clan
            if char_class.name.lower() == "vampire":
                vampire_clan = VampireClan.select().order_by(fn.Random()).limit(1).get()
            else:
                vampire_clan = None

            first_name, last_name = await fetch_random_name()

            # Create the character
            data: dict[str, str | int | bool] = {
                "first_name": first_name,
                "last_name": last_name,
                "nickname": char_class.name,
                "developer_character": True,
                "player_character": True,
            }

            character = self.bot.char_svc.update_or_add(
                ctx,
                data=data,
                char_class=char_class,
                clan=vampire_clan,
            )

            # Fetch all traits and set them
            fetched_traits = self.bot.trait_svc.fetch_all_class_traits(char_class.name)

            for trait in fetched_traits:
                character.set_trait_value(trait, randrange(0, 5))

            await present_embed(
                ctx,
                title="Test Character Created",
                fields=[
                    ("Name", character.name),
                    ("Owner", f"[{ctx.user.id}] {ctx.user.display_name}"),
                ],
                level="success",
                ephemeral=hidden,
            )

    @developer.command()
    @commands.is_owner()
    @commands.guild_only()
    async def delete_developer_characters(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete all developer characters from the database."""
        i = 0
        for character in Character.select().where(
            Character.data["developer_character"] == True  # noqa: E712
        ):
            character.delete_instance(recursive=True, delete_nullable=True)
            i += 1

        await present_embed(
            ctx,
            title="Developer characters deleted",
            description=f"Deleted {i} {p.plural_noun('character', i)}",
            level="success",
            ephemeral=hidden,
        )

    @developer.command()
    @commands.is_owner()
    async def debug_send_log(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Send the bot's logs to the user."""
        file = discord.File(self.bot.config["VALENTINA_LOG_FILE"])
        await ctx.respond(file=file, ephemeral=hidden)

    @developer.command(description="View last lines of the Valentina's logs")
    @commands.is_owner()
    async def debug_tail_logs(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the logs only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Tail the bot's logs."""
        logger.debug("ADMIN: Tail bot logs")
        max_lines_from_bottom = 20
        log_lines = []

        async with aiofiles.open(self.bot.config["VALENTINA_LOG_FILE"], mode="r") as f:
            async for line in f:
                if "has connected to Gateway" not in line:
                    log_lines.append(line)
                    if len(log_lines) > max_lines_from_bottom:
                        log_lines.pop(0)

        response = "".join(log_lines)
        await ctx.respond("```" + response[-MAX_CHARACTER_COUNT:] + "```", ephemeral=hidden)

    @developer.command()
    @commands.guild_only()
    @commands.is_owner()
    async def purge_cache(
        self,
        ctx: discord.ApplicationContext,
        all_guilds: Option(bool, default=False, required=False),
        with_claims: Option(
            bool,
            description="Purge user character claims (default: True)",
            default=False,
            required=False,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Purge the bot's cache and reload all data from the database."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Purge all caches?" if all_guilds else "Purge this guild's cache?",
            description="This will purge all caches and reload all data from the database"
            if all_guilds
            else "This will purge this guild's cache and reload all data from the database",
            level="info",
            ephemeral=True,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Cache Purge Cancelled",
                    color=EmbedColor.ERROR.value,
                )
            )
            return

        if not all_guilds:
            self.bot.guild_svc.purge_cache(ctx.guild)
            self.bot.user_svc.purge_cache(ctx)
            self.bot.char_svc.purge_cache(ctx, with_claims=with_claims)
            self.bot.chron_svc.purge_cache(ctx)
            self.bot.macro_svc.purge(ctx)
            logger.info(f"DEVELOPER: Purge cache for {ctx.guild.name}")

        if all_guilds:
            self.bot.guild_svc.purge_cache()
            self.bot.user_svc.purge_cache()
            self.bot.char_svc.purge_cache(with_claims=with_claims)
            self.bot.chron_svc.purge_cache()
            self.bot.macro_svc.purge()
            logger.info("DEVELOPER: Purge cache for all guilds")

        await msg.delete_original_response()
        await present_embed(
            ctx,
            title="All caches purged" if all_guilds else "Guild caches purged",
            level="success",
            ephemeral=hidden,
        )

    @developer.command(name="bot_reload")
    @commands.is_owner()
    async def reload(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the confirmation only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Reloads all cogs."""
        logger.debug("Admin: Reload the bot")
        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        embed = discord.Embed(title="Reload Cogs", color=EmbedColor.SUCCESS.value)
        embed.add_field(name="Status", value="Success")

        await ctx.respond(embed=embed, ephemeral=hidden)

    @developer.command()
    @commands.is_owner()
    async def servers(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the server list only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """List the servers the bot is connected to."""
        servers = list(self.bot.guilds)
        fields = []

        for n, i in enumerate(servers):
            fields.append(
                (
                    f"{n + 1}. {i.name}",
                    f"Members: `{i.member_count}`\nOwner: {i.owner.mention} (`{i.owner.id}`)",
                )
            )

        await present_embed(
            ctx,
            title="Connected guilds",
            description=f"Connected to {p.no('guild'), len(servers)}",
            level="info",
            fields=fields,
            ephemeral=hidden,
        )

    @developer.command(name="bot_shutdown")
    @commands.is_owner()
    async def shutdown(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the shutdown notification only visible to you (default False)",
            default=False,
        ),
    ) -> None:
        """Shutdown the bot."""
        logger.warning(f"DEVELOPER: {ctx.author.display_name} has shut down the bot")
        embed = discord.Embed(title="Shutting down Valentina...", color=EmbedColor.WARNING.value)
        await ctx.respond(embed=embed, ephemeral=hidden)
        await self.bot.close()

    @developer.command(name="bot_status")
    @commands.is_owner()
    async def status(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the server status only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Show server status information."""
        delta_uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        embed = discord.Embed(title="Connection Information", color=EmbedColor.INFO.value)
        embed.add_field(name="Status", value=str(self.bot.status))
        embed.add_field(name="Uptime", value=f"`{days}d, {hours}h, {minutes}m, {seconds}s`")
        embed.add_field(name="Latency", value=f"`{self.bot.latency!s}`")
        embed.add_field(name="Connected Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Bot Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Pycord Version", value=f"`{discord.__version__}`")
        embed.add_field(
            name="Database Version", value=f"`{self.bot.db_svc.fetch_database_version()}`"
        )

        await ctx.respond(embed=embed, ephemeral=hidden)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Developer(bot))
