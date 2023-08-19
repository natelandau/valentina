"""Compute and display statistics."""

import discord
from loguru import logger
from peewee import fn

from valentina.models.constants import EmbedColor, RollResultType
from valentina.models.db_tables import Character, RollStatistic


class Statistics:
    """Compute and display statistics.

    # TODO: Add support for pulling statistics for a specific time period.
    """

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
        statistics = {}

        for result_type in RollResultType:
            statistics[result_type.name] = 0

        # Determine the field to filter on
        filter_field = getattr(RollStatistic, field_name)

        # Confirm there are statistics to pull
        if not RollStatistic.select().where(filter_field == value).exists():
            logger.debug(f"No statistics found for `{field_name}: {value}`")
            return

        # Query for all statistics for the specific field and value
        logger.debug(f"Pulling statistics for `{field_name}: {value}`")
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

        self.botches = statistics[RollResultType.BOTCH.name]
        self.successes = statistics[RollResultType.SUCCESS.name]
        self.failures = statistics[RollResultType.FAILURE.name]
        self.criticals = statistics[RollResultType.CRITICAL.name]
        self.other = statistics[RollResultType.OTHER.name]

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
        self.total_rolls = (
            self.botches + self.successes + self.failures + self.criticals + self.other
        )
        logger.debug(f"Total rolls: {self.total_rolls}")
        return

    def get_text(self, with_title: bool = True) -> str:
        """Return a string with the statistics."""
        msg = "\n"
        if with_title:
            msg += f"## {self.title}\n"

        if self.total_rolls == 0:
            msg += "No statistics found"
            return msg

        msg += "```json\n"
        msg += f"Total Rolls: {'.':.<{22 - 12}} {self.total_rolls}\n"
        msg += f"Successes: {'.':.<{22 - 10}} {self.successes:<3} ({self.successes / self.total_rolls * 100:.2f}%)\n"
        msg += f"Failures: {'.':.<{22 - 9}} {self.failures:<3} ({self.failures / self.total_rolls * 100:.2f}%)\n"
        msg += f"Botches: {'.':.<{22 - 8}} {self.botches:<3} ({self.botches / self.total_rolls * 100:.2f}%)\n"
        msg += f"Critical Successes: {'.':.<{22 -19}} {self.criticals:<3} ({self.criticals / self.total_rolls * 100:.2f}%)\n"
        msg += f"Average Difficulty: {'.':.<{22 -19}} {self.average_difficulty}\n"
        msg += f"Average Pool Size: {'.':.<{22 -18}} {self.average_pool}\n"
        msg += "```"

        return msg

    async def get_embed(self) -> discord.Embed:
        """Return an embed with the statistics."""
        embed = discord.Embed(
            title="",
            description=self.get_text(),
            color=EmbedColor.INFO.value,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=self.thumbnail)

        return embed
