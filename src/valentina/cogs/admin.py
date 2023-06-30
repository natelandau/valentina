# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""
from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger
from sh import tail

from valentina import CONFIG, Valentina, __version__, guild_svc
from valentina.utils.converters import ValidChannelName
from valentina.views import ConfirmCancelButtons, present_embed


class Admin(commands.Cog):
    """Valentina settings, debugging, and administration."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    admin = discord.SlashCommandGroup("admin", "Administer Valentina")
    debug = admin.create_subgroup(name="debug", description="Debug the Valentina")
    settings = admin.create_subgroup(name="settings", description="Toggle Valentina settings")

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
        await present_embed(
            ctx,
            title="Manage Audit Log Settings",
            level="info",
            ephemeral=True,
            fields=fields,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
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

    ### DEBUG COMMANDS ################################################################
    @debug.command(description="View server latency")
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
            ],
            level="info",
            ephemeral=True,
        )

    @debug.command(description="Live reload Valentina")
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

    @debug.command(description="View last 15 lines of the Valentina's logs")
    @commands.has_permissions(administrator=True)
    async def logs(self, ctx: discord.ApplicationContext) -> None:
        """Tail the bot's logs."""
        logger.debug("debug:logs: Tailing the logs")
        logs = tail("-n15", CONFIG["VALENTINA_LOG_FILE"], _bg=True)
        await ctx.send("```" + str(logs) + "```")


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Admin(bot))
