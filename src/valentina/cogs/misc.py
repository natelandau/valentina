# mypy: disable-error-code="valid-type"
"""Miscellaneous commands."""

from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.models.bot import Valentina


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.slash_command()
    async def changlog(
        self,
        ctx: commands.Context,
        hidden: Option(
            bool,
            description="Make the changelog only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Display the bot's changelog."""
        path = Path(__file__).parent / "../../../CHANGELOG.md"
        changelog = path.read_text()

        # Embeds can take 4000 characters in the description field, but we keep
        # it at ~800 for the sake of not scrolling forever.
        paginator = discord.ext.commands.Paginator(prefix="", suffix="", max_size=800)

        for line in changelog.split("\n"):
            paginator.add_line(line)

        embeds = []
        for page in paginator.pages:
            embed = discord.Embed(
                title="Valentina Changelog",
                description=page,
                url="https://github.com/natelandau/valentina/releases",
            )
            embed.set_thumbnail(url=ctx.bot.user.display_avatar)
            embeds.append(embed)

        show_buttons = len(embeds) > 1
        paginator = discord.ext.pages.Paginator(  # type: ignore [attr-defined]
            embeds,
            author_check=False,
            show_disabled=show_buttons,
            show_indicator=show_buttons,
        )
        await paginator.respond(ctx.interaction, ephemeral=hidden)  # type: ignore [attr-defined]


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Misc(bot))
