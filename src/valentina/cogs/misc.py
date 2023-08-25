# mypy: disable-error-code="valid-type"
"""Miscellaneous commands."""

import random
from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.slash_command(description="Display the bot's changelog")
    async def changelog(
        self,
        ctx: commands.Context,
        hidden: Option(
            bool,
            description="Make the changelog only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Display the bot's changelog.

        Args:
            ctx (commands.Context): The context of the command.
            hidden (Option[bool]): Whether to make the changelog only visible to you (default true).
        """
        # Determine the path to the changelog file
        path = Path(__file__).parent / "../../../CHANGELOG.md"
        if not path.exists():
            logger.error(f"Changelog file not found at {path}")
            raise FileNotFoundError

        changelog = path.read_text()

        # Use paginator to split the changelog into pages
        paginator = discord.ext.commands.Paginator(prefix="", suffix="", max_size=800)
        for line in changelog.split("\n"):
            paginator.add_line(line)

        # Create embeds for each page of the changelog
        pages_to_send = [
            discord.Embed(
                title="Valentina Changelog",
                description=page,
                url="https://github.com/natelandau/valentina/releases",
            ).set_thumbnail(url=ctx.bot.user.display_avatar)
            for page in paginator.pages
        ]

        show_buttons = len(pages_to_send) > 1
        paginator = discord.ext.pages.Paginator(  # type: ignore [assignment]
            pages=pages_to_send,  # type: ignore [arg-type]
            author_check=False,
            show_disabled=show_buttons,
            show_indicator=show_buttons,
        )
        await paginator.respond(ctx.interaction, ephemeral=hidden)  # type: ignore

    @commands.slash_command(name="coinflip", help="Flip a coin")
    async def coinflip(self, ctx: discord.ApplicationContext) -> None:
        """Coinflip!"""
        coinsides = ["Heads", "Tails"]
        await ctx.respond(
            f"**{ctx.author.name}** flipped a coin and got **{random.choice(coinsides)}**!"
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Misc(bot))
