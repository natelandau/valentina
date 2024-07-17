"""Compute and display statistics."""

from datetime import datetime
from typing import TYPE_CHECKING

import discord
from beanie import Document, Indexed
from pydantic import Field

from valentina.constants import EmbedColor, RollResultType
from valentina.models import Campaign, Character, Guild
from valentina.utils import errors
from valentina.utils.helpers import time_now

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


class RollStatistic(Document):
    """Track roll results for statistics."""

    user: Indexed(int)  # type: ignore [valid-type]
    guild: Indexed(int)  # type: ignore [valid-type]
    character: Indexed(str) | None = None  # type: ignore [valid-type]
    result: RollResultType
    pool: int
    difficulty: int
    date_rolled: datetime = Field(default_factory=time_now)
    traits: list[str] = Field(default_factory=list)
    campaign: Indexed(str) | None = None  # type: ignore [valid-type]


class Statistics:
    """Compute and display roll statistics."""

    def __init__(
        self,
        ctx: "ValentinaContext" = None,
        guild_id: int | None = None,
    ) -> None:
        self.ctx = ctx
        self.guild_id = guild_id
        self.botches = 0
        self.successes = 0
        self.failures = 0
        self.criticals = 0
        self.total_rolls = 0
        self.average_difficulty = 0
        self.average_pool = 0
        self.title = "Roll Statistics"
        self.thumbnail = ""

    @property
    def criticals_percentage(self) -> str:
        """Return the percentage of critical successes."""
        return f"{self.criticals / self.total_rolls * 100:.2f}" if self.total_rolls > 0 else "0"

    @property
    def success_percentage(self) -> str:
        """Return the percentage of successful rolls."""
        return f"{self.successes / self.total_rolls * 100:.2f}" if self.total_rolls > 0 else "0"

    @property
    def failure_percentage(self) -> str:
        """Return the percentage of failed rolls."""
        return f"{self.failures / self.total_rolls * 100:.2f}" if self.total_rolls > 0 else "0"

    @property
    def botch_percentage(self) -> str:
        """Return the percentage of botched rolls."""
        return f"{self.botches / self.total_rolls * 100:.2f}" if self.total_rolls > 0 else "0"

    def _get_json(self) -> dict[str, str]:
        """Return a dictionary with the statistics.

        Returns:
            dict: Dictionary with the statistics.
        """
        return {
            "total_rolls": str(self.total_rolls),
            "criticals": str(self.criticals),
            "criticals_percentage": self.criticals_percentage,
            "successes": str(self.successes),
            "successes_percentage": self.success_percentage,
            "failures": str(self.failures),
            "failures_percentage": self.failure_percentage,
            "botches": str(self.botches),
            "botches_percentage": self.botch_percentage,
            "average_difficulty": str(self.average_difficulty),
            "average_pool": str(self.average_pool),
        }

    def _get_text(self, with_title: bool = True, with_help: bool = True) -> str:
        """Return a string with the statistics.

        Args:
            with_title (bool, optional): Whether to include the title. Defaults to True.
            with_help (bool, optional): Whether to include the help text. Defaults to True.

        Returns:
            str: String with the statistics.
        """
        msg = "\n"
        if with_title:
            msg += f"## {self.title}\n"

        if self.total_rolls == 0:
            msg += "No statistics found"
            return msg

        msg += f"""\
`Total Rolls {'.':.<{25 - 12}} {self.total_rolls}`
`Critical Success Rolls {'.':.<{25 - 23}} {self.criticals:<3} ({self.criticals_percentage}%)`
`Successful Rolls {'.':.<{25 - 17}} {self.successes:<3} ({self.success_percentage}%)`
`Failed Rolls {'.':.<{25 - 13}} {self.failures:<3} ({self.failure_percentage}%)`
`Botched Rolls {'.':.<{25 - 14}} {self.botches:<3} ({self.botch_percentage}%)`
`Average Difficulty {'.':.<{25 - 19}} {self.average_difficulty}`
`Average Pool Size {'.':.<{25 - 18}} {self.average_pool}`
"""

        if with_help:
            msg += """
> Definitions:
> - _Critical Success_: More successes than dice rolled
> - _Success_: At least one success after all dice are tallied
> - _Failure_: Zero successes after all dice are tallied
> - _Botch_: Negative successes after all dice are tallied
"""
        return msg

    async def _get_embed(self, with_title: bool = True, with_help: bool = True) -> discord.Embed:
        """Return an embed with the statistics.

        Returns:
            discord.Embed: Embed with the statistics.
        """
        if not self.ctx:
            msg = "No context provided."
            raise errors.NoCTXError(msg)

        embed = discord.Embed(
            title="",
            description=self._get_text(with_title=with_title, with_help=with_help),
            color=EmbedColor.INFO.value,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=self.thumbnail)
        embed.set_footer(
            text=f"Requested by {self.ctx.author}",
            icon_url=self.ctx.author.display_avatar.url,
        )
        return embed

    async def guild_statistics(
        self,
        as_embed: bool = False,
        as_json: bool = False,
        with_title: bool = True,
        with_help: bool = True,
    ) -> discord.Embed | str | dict[str, str]:
        """Compute and display guild statistics.

        Args:
            as_embed (bool, optional): Whether to return an embed. Defaults to False. When False, returns a string.
            as_json (bool, optional): Whether to return a JSON object. Defaults to False.
            with_title (bool, optional): Whether to include the title. Defaults to True.
            with_help (bool, optional): Whether to include the help text. Defaults to True.

        Returns:
            discord.Embed | str: Embed or string with the statistics.
        """
        if not self.ctx and not self.guild_id:
            msg = "No context or guild ID provided."
            raise errors.NoCTXError(msg)

        guild_id = self.guild_id or self.ctx.guild.id

        if not self.ctx:
            guild_object = await Guild.get(guild_id)

        self.title = (
            f"Roll statistics for guild `{self.ctx.guild.name}`" if self.ctx else guild_object.name
        )
        if self.ctx:
            self.thumbnail = self.ctx.guild.icon.url if self.ctx.guild.icon else ""

        # Grab the data from the database
        self.botches = await RollStatistic.find(
            RollStatistic.guild == guild_id,
            RollStatistic.result == RollResultType.BOTCH,
        ).count()
        self.successes = await RollStatistic.find(
            RollStatistic.guild == guild_id,
            RollStatistic.result == RollResultType.SUCCESS,
        ).count()
        self.criticals = await RollStatistic.find(
            RollStatistic.guild == guild_id,
            RollStatistic.result == RollResultType.CRITICAL,
        ).count()
        self.failures = await RollStatistic.find(
            RollStatistic.guild == guild_id,
            RollStatistic.result == RollResultType.FAILURE,
        ).count()
        self.other = await RollStatistic.find(
            RollStatistic.guild == guild_id,
            RollStatistic.result == RollResultType.OTHER,
        ).count()

        avg_diff = await RollStatistic.find(RollStatistic.guild == guild_id).avg(
            RollStatistic.difficulty
        )
        if avg_diff:
            self.average_difficulty = round(avg_diff)

        avg_pool = await RollStatistic.find(RollStatistic.guild == guild_id).avg(RollStatistic.pool)
        if avg_pool:
            self.average_pool = round(avg_pool)

        # Calculate total rolls
        self.total_rolls = (
            self.botches + self.successes + self.failures + self.criticals + self.other
        )

        if as_embed:
            return await self._get_embed(with_title=with_title, with_help=with_help)

        if as_json:
            return self._get_json()

        return self._get_text(with_title=with_title, with_help=with_help)

    async def user_statistics(
        self,
        user: discord.Member,
        as_embed: bool = False,
        as_json: bool = False,
        with_title: bool = True,
        with_help: bool = True,
    ) -> discord.Embed | str | dict[str, str]:
        """Compute and display user statistics.

        Args:
            user (discord.Member): The user to get statistics for.
            as_embed (bool, optional): Whether to return an embed. Defaults to False. When False, returns a string.
            as_json (bool, optional): Whether to return a JSON object. Defaults to False.
            with_title (bool, optional): Whether to include the title. Defaults to True.
            with_help (bool, optional): Whether to include the help text. Defaults to True.

        Returns:
            discord.Embed | str: Embed or string with the statistics.
        """
        if not as_json:
            self.title = f"Roll statistics for @{user.display_name}"
            self.thumbnail = user.display_avatar.url

        # Grab the data from the database
        self.botches = await RollStatistic.find(
            RollStatistic.user == user.id,
            RollStatistic.result == RollResultType.BOTCH,
        ).count()
        self.successes = await RollStatistic.find(
            RollStatistic.user == user.id,
            RollStatistic.result == RollResultType.SUCCESS,
        ).count()
        self.criticals = await RollStatistic.find(
            RollStatistic.user == user.id,
            RollStatistic.result == RollResultType.CRITICAL,
        ).count()
        self.failures = await RollStatistic.find(
            RollStatistic.user == user.id,
            RollStatistic.result == RollResultType.FAILURE,
        ).count()
        self.other = await RollStatistic.find(
            RollStatistic.user == user.id,
            RollStatistic.result == RollResultType.OTHER,
        ).count()

        avg_diff = await RollStatistic.find(RollStatistic.user == user.id).avg(
            RollStatistic.difficulty
        )
        if avg_diff:
            self.average_difficulty = round(avg_diff)

        avg_pool = await RollStatistic.find(RollStatistic.user == user.id).avg(RollStatistic.pool)
        if avg_pool:
            self.average_pool = round(avg_pool)

        # Calculate total rolls
        self.total_rolls = (
            self.botches + self.successes + self.failures + self.criticals + self.other
        )

        if as_embed:
            return await self._get_embed(with_title=with_title, with_help=with_help)

        if as_json:
            return self._get_json()

        return self._get_text(with_title=with_title, with_help=with_help)

    async def character_statistics(
        self,
        character: Character,
        as_embed: bool = False,
        as_json: bool = False,
        with_title: bool = True,
        with_help: bool = True,
    ) -> discord.Embed | str | dict[str, str]:
        """Compute and display character statistics.

        Args:
            character (Character): The character to get statistics for.
            as_embed (bool, optional): Whether to return an embed. Defaults to False. When False, returns a string.
            as_json (bool, optional): Whether to return a JSON object. Defaults to False.
            with_title (bool, optional): Whether to include the title. Defaults to True.
            with_help (bool, optional): Whether to include the help text. Defaults to True.

        Returns:
            discord.Embed | str: Embed or string with the statistics.
        """
        self.title = f"Roll statistics for {character.name}"

        # Grab the data from the database
        self.botches = await RollStatistic.find(
            RollStatistic.character == str(character.id),
            RollStatistic.result == RollResultType.BOTCH,
        ).count()
        self.successes = await RollStatistic.find(
            RollStatistic.character == str(character.id),
            RollStatistic.result == RollResultType.SUCCESS,
        ).count()
        self.criticals = await RollStatistic.find(
            RollStatistic.character == str(character.id),
            RollStatistic.result == RollResultType.CRITICAL,
        ).count()
        self.failures = await RollStatistic.find(
            RollStatistic.character == str(character.id),
            RollStatistic.result == RollResultType.FAILURE,
        ).count()
        self.other = await RollStatistic.find(
            RollStatistic.character == str(character.id),
            RollStatistic.result == RollResultType.OTHER,
        ).count()

        avg_diff = await RollStatistic.find(RollStatistic.character == str(character.id)).avg(
            RollStatistic.difficulty
        )
        if avg_diff:
            self.average_difficulty = round(avg_diff)

        avg_pool = await RollStatistic.find(RollStatistic.character == str(character.id)).avg(
            RollStatistic.pool
        )
        if avg_pool:
            self.average_pool = round(avg_pool)

        # Calculate total rolls
        self.total_rolls = (
            self.botches + self.successes + self.failures + self.criticals + self.other
        )

        if as_embed:
            return await self._get_embed(with_title=with_title, with_help=with_help)

        if as_json:
            return self._get_json()

        return self._get_text(with_title=with_title, with_help=with_help)

    async def campaign_statistics(
        self,
        campaign: Campaign,
        as_embed: bool = False,
        as_json: bool = False,
        with_title: bool = True,
        with_help: bool = True,
    ) -> discord.Embed | str | dict[str, str]:
        """Compute and display character statistics.

        Args:
            campaign (Campaign): The campaign to get statistics for.
            as_embed (bool, optional): Whether to return an embed. Defaults to False. When False, returns a string.
            as_json (bool, optional): Whether to return a JSON object. Defaults to False.
            with_title (bool, optional): Whether to include the title. Defaults to True.
            with_help (bool, optional): Whether to include the help text. Defaults to True.

        Returns:
            discord.Embed | str: Embed or string with the statistics.
        """
        self.title = f"Roll statistics for {campaign.name}"

        # Grab the data from the database
        self.botches = await RollStatistic.find(
            RollStatistic.campaign == str(campaign.id),
            RollStatistic.result == RollResultType.BOTCH,
        ).count()
        self.successes = await RollStatistic.find(
            RollStatistic.campaign == str(campaign.id),
            RollStatistic.result == RollResultType.SUCCESS,
        ).count()
        self.criticals = await RollStatistic.find(
            RollStatistic.campaign == str(campaign.id),
            RollStatistic.result == RollResultType.CRITICAL,
        ).count()
        self.failures = await RollStatistic.find(
            RollStatistic.campaign == str(campaign.id),
            RollStatistic.result == RollResultType.FAILURE,
        ).count()
        self.other = await RollStatistic.find(
            RollStatistic.campaign == str(campaign.id),
            RollStatistic.result == RollResultType.OTHER,
        ).count()

        avg_diff = await RollStatistic.find(RollStatistic.campaign == str(campaign.id)).avg(
            RollStatistic.difficulty
        )
        if avg_diff:
            self.average_difficulty = round(avg_diff)

        avg_pool = await RollStatistic.find(RollStatistic.campaign == str(campaign.id)).avg(
            RollStatistic.pool
        )
        if avg_pool:
            self.average_pool = round(avg_pool)

        # Calculate total rolls
        self.total_rolls = (
            self.botches + self.successes + self.failures + self.criticals + self.other
        )

        if as_embed:
            return await self._get_embed(with_title=with_title, with_help=with_help)

        if as_json:
            return self._get_json()

        return self._get_text(with_title=with_title, with_help=with_help)
