"""Compute and display statistics."""

import discord
from loguru import logger
from peewee import fn

from valentina.models.constants import EmbedColor
from valentina.models.db_tables import Character, RollStatistic


class Statistics:
    """Compute and display statistics."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member = None,
        character: Character | None = None,
    ) -> None:
        self.ctx = ctx
        self.user = user
        self.character = character
        self.botches = 0
        self.successes = 0
        self.failures = 0
        self.criticals = 0
        self.total_rolls = 0
        self.average_difficulty = 0
        self.average_pool = 0
        self.title = "Roll Statistics"

        # Pull statistics
        if self.user:
            self._pull_statistics("user", self.user.id)
            self.title += f" for `{self.user.display_name}`"
            self.thumbnail = self.user.display_avatar.url
        elif self.character:
            self._pull_statistics("character", self.character)
            self.title += f" for `{self.character.name}`"
            self.thumbnail = ""
        else:
            self._pull_statistics("guild", self.ctx.guild.id)
            self.title += f" for guild `{self.ctx.guild.name}`"
            self.thumbnail = self.ctx.guild.icon or ""

    def _pull_statistics(self, field_name: str, value: int) -> None:
        """Pull statistics from the database based on the given field and value."""
        # Initialize counts
        statistics = {
            "botch": 0,
            "success": 0,
            "failure": 0,
            "critical": 0,
        }

        # Determine the field to filter on
        filter_field = getattr(RollStatistic, field_name)

        # Confirm there are statistics to pull
        if not RollStatistic.select().where(filter_field == value).exists():
            logger.debug(f"No statistics found for `{field_name}: {value}`")
            return

        # Query for all statistics for the specific field and value
        query = (
            RollStatistic.select(
                RollStatistic.result, fn.COUNT(RollStatistic.result).alias("count")
            )
            .where(filter_field == value)
            .group_by(RollStatistic.result)
        )

        # Update counts based on query results
        for stat in query:
            statistics[stat.result] = stat.count

        self.botches = statistics["botch"]
        self.successes = statistics["success"]
        self.failures = statistics["failure"]
        self.criticals = statistics["critical"]

        # Query for average difficulty and pool
        self.average_difficulty = round(
            RollStatistic.select(fn.AVG(RollStatistic.difficulty).alias("average_difficulty"))
            .where(filter_field == value)
            .scalar()
        )
        self.average_pool = round(
            RollStatistic.select(fn.AVG(RollStatistic.pool).alias("average_pool"))
            .where(filter_field == value)
            .scalar()
        )

        # Calculate total rolls
        self.total_rolls = self.botches + self.successes + self.failures + self.criticals
        return

    def get_text(self, with_title: bool = True) -> str:
        """Return a string with the statistics."""
        msg = "\n"
        if with_title:
            msg += f"**{self.title}**\n"

        if self.total_rolls == 0:
            msg += "No statistics found"
            return msg

        msg += f"Total Rolls: `{self.total_rolls}`\n"
        msg += f"Successes: `{self.successes}`\n"
        msg += f"Failures: `{self.failures}`\n"
        msg += f"Botches: `{self.botches}`\n"
        msg += f"Critical Successes: `{self.criticals}`\n"
        msg += f"Average Difficulty: `{self.average_difficulty}`\n"
        msg += f"Average Pool Size: `{self.average_pool}`\n"

        return msg

    async def get_embed(self) -> discord.Embed:
        """Return an embed with the statistics."""
        embed = discord.Embed(
            title=self.title, color=EmbedColor.INFO.value, timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=self.thumbnail)

        if self.total_rolls == 0:
            embed.description = "No statistics found."
            return embed

        embed.add_field(name="Total Rolls", value=str(self.total_rolls))
        embed.add_field(name="Successes", value=str(self.successes))
        embed.add_field(name="Failures", value=str(self.failures))
        embed.add_field(name="Botches", value=str(self.botches))
        embed.add_field(name="Critical Successes", value=str(self.criticals))
        embed.add_field(name="Average Difficulty", value=str(self.average_difficulty))
        embed.add_field(name="Average Pool size", value=str(self.average_pool))
        return embed

    def run(self) -> None:
        """Run the statistics engine."""
        from rich.console import Console

        c = Console()
        c.rule("Statistics")
        c.print(f"Total Rolls: {self.total_rolls}")
        c.print(f"Successes: {self.successes}")
        c.print(f"Failures: {self.failures}")
        c.print(f"Botches: {self.botches}")
        c.print(f"Criticals: {self.criticals}")
        c.print(f"Average Difficulty: {self.average_difficulty}")
        c.print(f"Average Pool: {self.average_pool}")
        c.rule()
