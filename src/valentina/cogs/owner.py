"""Commands for the owner of the bot."""
from datetime import datetime
from pathlib import Path

import aiofiles
import discord
import inflect
from discord.ext import commands
from loguru import logger

from valentina.constants import MAX_CHARACTER_COUNT, EmbedColor
from valentina.models.bot import Valentina

p = inflect.engine()


class Owner(commands.Cog):
    """Owner commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.command(name="db_backup")
    @commands.is_owner()
    @logger.catch
    async def db_backup(self, ctx: discord.ApplicationContext) -> None:
        """Create a backup of the database."""
        logger.info("ADMIN: Manually create database backup")
        db_file = await self.bot.db_svc.backup_database(self.bot.config)
        embed = discord.Embed(
            title="Database backup created",
            color=EmbedColor.SUCCESS.value,
        )
        embed.add_field(name="File", value=f"`{db_file}`")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def serverlist(self, ctx: discord.ApplicationContext) -> None:
        """List the servers the bot is connected to."""
        servers = list(self.bot.guilds)

        embed = discord.Embed(
            title="Connected guilds",
            description=f"Connected to {p.no('guild'), len(servers)}",
            color=0x20BEFF,
        )
        for n, i in enumerate(servers):
            embed.add_field(
                name=f"{n + 1}. {i.name}",
                value=f"Members: `{i.member_count}`\nOwner: {i.owner.mention} (`{i.owner.id}`)",
            )

            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext) -> None:
        """Shutdown the bot."""
        logger.warning(f"ADMIN: {ctx.author.display_name} has shut down the bot")
        embed = discord.Embed(title="Shutting down Valentina...", color=EmbedColor.WARNING.value)
        await ctx.send(embed=embed)
        await self.bot.close()

    @commands.command(description="View last lines of the Valentina's logs")
    async def tail_logs(self, ctx: discord.ApplicationContext) -> None:
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
        await ctx.send("```" + response[-MAX_CHARACTER_COUNT:] + "```")

    @commands.command()
    @commands.is_owner()
    async def send_log(self, ctx: discord.ApplicationContext) -> None:
        """Send the bot's logs to the user."""
        file = discord.File(self.bot.config["VALENTINA_LOG_FILE"])
        await ctx.author.send(file=file)

    @commands.command()
    @commands.is_owner()
    async def status(self, ctx: discord.ApplicationContext) -> None:
        """Show server status information."""
        logger.debug("ADMIN: Show server status information")

        delta_uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        embed = discord.Embed(
            title="Connection Information",
            color=EmbedColor.INFO.value,
        )
        embed.add_field(name="Status", value=str(self.bot.status))
        embed.add_field(name="Uptime", value=f"`{days}d, {hours}h, {minutes}m, {seconds}s`")
        embed.add_field(name="Latency", value=f"`{self.bot.latency!s}`")
        embed.add_field(name="Connected Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Bot Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Pycord Version", value=f"`{discord.__version__}`")
        embed.add_field(
            name="Database Version", value=f"`{self.bot.db_svc.fetch_current_version()}`"
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: discord.ApplicationContext) -> None:
        """Reloads all cogs."""
        logger.debug("Admin: Reload the bot")
        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        embed = discord.Embed(
            title="Reload Bot",
            color=EmbedColor.SUCCESS.value,
        )
        embed.add_field(name="Status", value="Success")

        await ctx.send(embed=embed)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Owner(bot))
