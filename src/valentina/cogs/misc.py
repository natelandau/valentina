# mypy: disable-error-code="valid-type"
"""Miscellaneous commands."""
import random

import discord
import semver
from discord.commands import Option
from discord.ext import commands

from valentina.constants import SPACER, DiceType, EmbedColor
from valentina.models import Probability, Statistics
from valentina.models.bot import Valentina
from valentina.models.db_tables import Character, Macro
from valentina.utils.changelog_parser import ChangelogParser
from valentina.utils.options import select_changelog_version_1, select_changelog_version_2


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    @commands.slash_command(name="probability", description="Calculate the probability of a roll")
    async def probability(
        self,
        ctx: discord.ApplicationContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the probability only visible to you (default False)",
            default=False,
        ),
    ) -> None:
        """Roll the dice.

        Args:
            hidden (bool, optional): Make the statistics only visible to you (default true). Defaults to True.
            ctx (discord.ApplicationContext): The context of the command
            difficulty (int): The difficulty of the roll
            pool (int): The number of dice to roll
        """
        probabilities = Probability(
            ctx, pool=pool, difficulty=difficulty, dice_size=DiceType.D10.value
        )
        embed = await probabilities.get_embed()
        await ctx.respond(embed=embed, ephemeral=hidden)

    @commands.slash_command(name="user_info", description="View information about a user")
    async def user_info(
        self,
        ctx: discord.ApplicationContext,
        user: Option(
            discord.User,
            description="The user to view information for",
            required=False,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default False).",
            default=False,
        ),
    ) -> None:
        """View information about a user."""
        target = user or ctx.author
        db_user = await self.bot.user_svc.fetch_user(ctx=ctx, user=target)

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
        lifetime_xp = db_user.data.get("lifetime_experience", 0)
        lifetime_cp = db_user.data.get("lifetime_cool_points", 0)
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        campaign_xp = db_user.data.get(f"{campaign.id}_experience", 0)
        campaign_total_xp = db_user.data.get(f"{campaign.id}_total_experience", 0)
        campaign_cp = db_user.data.get(f"{campaign.id}_total_cool_points", 0)

        # Build Embed
        description = (
            f"# {target.display_name}",
            "### __Account Information__",
            f"**Account Created :** <t:{creation_date}:R> on <t:{creation_date}:D>",
            f"**Joined Server{SPACER * 7}:** <t:{int(target.joined_at.timestamp())}:R> on <t:{int(target.joined_at.timestamp())}:D>",
            f"**Roles{SPACER * 24}:** {roles}",
            "### __Campaign Information__",
            f"Available Experience{SPACER * 2}: `{campaign_xp}`",
            f"Total Experience{SPACER * 10}: `{campaign_total_xp}`",
            f"Cool Points{SPACER * 20}: `{campaign_cp}`",
            "### __Experience Information__",
            f"Lifetime Experience{SPACER * 3}: `{lifetime_xp}`",
            f"Lifetime Cool Points{SPACER * 2}: `{lifetime_cp}`",
            "### __Gameplay Information__",
            f"Player Characters{SPACER * 2}: `{num_characters}`",
            f"Roll Macros{SPACER * 14}: `{num_macros}`",
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

    @commands.slash_command(name="changelog", description="Display the bot's changelog")
    async def post_changelog(
        self,
        ctx: discord.ApplicationContext,
        oldest_version: Option(str, autocomplete=select_changelog_version_1, required=True),
        newest_version: Option(str, autocomplete=select_changelog_version_2, required=True),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Post the changelog."""
        if semver.compare(oldest_version, newest_version) > 0:
            raise commands.BadArgument(
                f"Oldest version `{oldest_version}` is newer than newest version `{newest_version}`"
            )

        changelog = ChangelogParser(self.bot, oldest_version, newest_version)
        embed = changelog.get_embed()
        await ctx.respond(embed=embed, ephemeral=hidden)

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
