# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""

from pathlib import Path

import aiofiles
import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import (
    CONFIG,
    Valentina,
    __version__,
    char_svc,
    chron_svc,
    db_svc,
    guild_svc,
    user_svc,
)
from valentina.models.constants import MAX_CHARACTER_COUNT
from valentina.utils.converters import ValidChannelName
from valentina.views import ConfirmCancelButtons, present_embed


class Admin(commands.Cog):
    """Valentina settings, debugging, and administration."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    administration = discord.SlashCommandGroup("admin", "Administer Valentina")
    server = administration.create_subgroup(
        name="server", description="Run server administration commands"
    )
    settings = administration.create_subgroup(
        name="settings", description="Toggle Valentina settings"
    )

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        command_name = ""
        if ctx.command.parent.name:
            command_name = f"{ctx.command.parent.name} "
        command_name += ctx.command.name

        await present_embed(
            ctx,
            title=f"Error running `{command_name}` command",
            description=str(error),
            level="error",
            ephemeral=True,
            delete_after=15,
        )

    ### SETTINGS COMMANDS #############################################################
    @settings.command(description="Toggle audit log on/off")
    @commands.has_permissions(administrator=True)
    async def audit_log(
        self,
        ctx: discord.ApplicationContext,
        channel_name: Option(
            ValidChannelName, "Audit log channel name", required=False, default=None
        ),
    ) -> None:
        """Toggle audit log on/off."""
        setting = guild_svc.is_audit_logging(ctx)
        if setting:
            fields = [
                ("Current audit log status", "Enabled"),
                ("\u200b", "**Disable logging to audit channel?**"),
            ]
        else:
            fields = [
                ("Current audit log status", "Disabled"),
                ("\u200b", "**Enable logging to audit channel?**"),
            ]

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Manage Audit Log Settings",
            level="info",
            ephemeral=True,
            fields=fields,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(title="Setting change cancelled", color=discord.Color.red())
            )
            return

        if setting:
            await guild_svc.send_log(ctx, "Audit logging disabled")
            guild_svc.set_audit_log(ctx, False)
            return

        if not guild_svc.fetch_log_channel(ctx) and not channel_name:
            await present_embed(
                ctx,
                title="No audit log channel",
                description="Please rerun the command and enter a channel name",
                level="error",
                ephemeral=True,
            )
            return

        if not guild_svc.fetch_log_channel(ctx) and channel_name:
            await guild_svc.create_bot_log_channel(ctx.guild, channel_name)
            guild_svc.set_audit_log(ctx, True)
            message = f"Logging to channel **{channel_name}**"
        else:
            guild_svc.set_audit_log(ctx, True)
            message = "Logging to audit channel enabled"

        await present_embed(ctx, title=message, level="success", ephemeral=True, log=True)

    ### SERVER COMMANDS ################################################################
    @server.command(description="View server latency")
    async def ping(self, ctx: discord.ApplicationContext) -> None:
        """Ping the bot to get debug information."""
        logger.debug("debug:ping: Generating debug information")
        await present_embed(
            ctx,
            title="Connection Information",
            description="",
            fields=[
                ("Status", str(self.bot.status)),
                ("Latency", f"`{self.bot.latency!s}`"),
                ("Connected Guilds", str(len(self.bot.guilds))),
                ("Bot Version", f"`{__version__}`"),
                ("Database Version", f"`{db_svc.database_version()}`"),
            ],
            inline_fields=True,
            level="info",
            ephemeral=True,
        )

    @server.command(description="Live reload Valentina")
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx: discord.ApplicationContext) -> None:
        """Reloads all cogs."""
        logger.debug("debug:reload: Reloading the bot...")
        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        await present_embed(
            ctx, "Reload Bot", f"{count} cogs successfully reloaded", level="info", ephemeral=True
        )

    @server.command(description="View last lines of the Valentina's logs")
    @commands.has_permissions(administrator=True)
    async def tail_logs(self, ctx: discord.ApplicationContext) -> None:
        """Tail the bot's logs."""
        logger.debug("debug:logs: Tailing the logs")
        max_lines_from_bottom = 20
        log_lines = []

        async with aiofiles.open(CONFIG["VALENTINA_LOG_FILE"], mode="r") as f:
            async for line in f:
                if "has connected to Gateway" not in line:
                    log_lines.append(line)
                    if len(log_lines) > max_lines_from_bottom:
                        log_lines.pop(0)

        response = "".join(log_lines)
        await ctx.respond("```" + response[-MAX_CHARACTER_COUNT:] + "```", ephemeral=True)

    @server.command(description="Purge the bot's cache and reload data from DB")
    @commands.has_permissions(administrator=True)
    @logger.catch
    async def puge_cache(
        self,
        ctx: discord.ApplicationContext,
        all_guilds: Option(bool, choices=[True, False], default=False, required=False),
    ) -> None:
        """Purge the bot's cache and reload all data from DB."""
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
                    color=discord.Color.red(),
                )
            )
            return

        if not all_guilds:
            guild_svc.purge_cache(ctx)
            user_svc.purge_cache(ctx)
            char_svc.purge_cache(ctx, with_claims=True)
            chron_svc.purge_cache(ctx)
            logger.info(f"debug:cache: Purged cache for {ctx.guild.name}")

        if all_guilds:
            guild_svc.purge_cache()
            user_svc.purge_cache()
            char_svc.purge_cache(with_claims=True)
            chron_svc.purge_cache()
            logger.info("debug:cache: Purged cache for all guilds")

        await msg.delete_original_response()
        await present_embed(
            ctx,
            title="All caches purged" if all_guilds else "Guild caches purged",
            level="success",
            ephemeral=True,
            log=True,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Admin(bot))
