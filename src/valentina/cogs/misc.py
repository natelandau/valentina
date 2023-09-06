# mypy: disable-error-code="valid-type"
"""Miscellaneous commands."""

import random
from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.constants import SPACER, EmbedColor
from valentina.models import Statistics
from valentina.models.bot import Valentina
from valentina.models.db_tables import Character, Macro


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.slash_command(name="user_info", description="View information about a user")
    @discord.guild_only()
    async def user_info(
        self,
        ctx: discord.ApplicationContext,
        user: Option(
            discord.User,
            description="The user to view information for",
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default False).",
            default=False,
        ),
    ) -> None:
        """View information about a user."""
        target = user or ctx.author
        db_user = self.bot.user_svc.fetch_user(ctx=ctx)

        # Variables for embed
        num_characters = (
            Character.select()
            .where(
                Character.guild == ctx.guild.id,
                Character.data["player_character"] == True,  # noqa: E712
                Character.owned_by == db_user,
            )
            .count()
        )
        num_macros = (
            Macro.select().where(Macro.guild == ctx.guild.id, Macro.user == db_user).count()
        )

        creation_date = ((target.id >> 22) + 1420070400000) // 1000
        roles = ", ".join(r.mention for r in target.roles[::-1][:-1]) or "_Member has no roles_"
        roll_stats = Statistics(ctx, user=target)

        # Build Embed
        description = (
            f"# {target.display_name}",
            "### __Account Information__",
            f"**Account Created :** <t:{creation_date}:R> on <t:{creation_date}:D>",
            f"**Joined Server{SPACER * 7}:** <t:{int(target.joined_at.timestamp())}:R> on <t:{int(target.joined_at.timestamp())}:D>",
            f"**Roles{SPACER * 24}:** {roles}",
            "### __Gameplay Information__",
            f"**Player Characters :** `{num_characters}`",
            f"**Roll Macros{SPACER * 14}:** `{num_macros}`",
            "### __Roll Statistics__",
            roll_stats.get_text(with_title=False),
        )

        embed = discord.Embed(
            title="",
            description="\n".join(description),
            color=EmbedColor.INFO.value,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        embed.timestamp = discord.utils.utcnow()

        await ctx.respond(embed=embed, ephemeral=hidden)

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
        coin_sides = ["Heads", "Tails"]
        await ctx.respond(
            f"**{ctx.author.name}** flipped a coin and got **{random.choice(coin_sides)}**!"
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Misc(bot))
