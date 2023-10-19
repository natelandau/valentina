# type: ignore
"""Test the CharacterService class."""
import re

import discord
import pytest
from dirty_equals import IsInstance, IsStr

from valentina.constants import RollResultType
from valentina.models import Statistics
from valentina.models.sqlite_models import Character, RollStatistic


@pytest.mark.usefixtures("mock_db")
class TestStatistics:
    """Test the Statistics class."""

    @pytest.mark.asyncio()
    async def test_guild_statistics(self, mock_ctx):
        """Test pulling guild statistics."""
        # GIVEN no statistics in the db
        for record in RollStatistic.select():
            record.delete_instance(recursive=True, delete_nullable=True)

        # WHEN statistics are pulled for a guild
        s = Statistics(mock_ctx)
        embed = await s.get_embed()

        # THEN confirm users are told there are no statistics to display
        assert s.botches == 0
        assert s.successes == 0
        assert s.failures == 0
        assert s.criticals == 0
        assert s.total_rolls == 0
        assert s.average_difficulty == 0
        assert s.average_pool == 0
        assert s.title == "Roll Statistics for guild `Test Guild`"
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*No statistics found", regex_flags=re.S)

        # GIVEN rolls in the database
        for result, pool, difficulty in zip(
            RollResultType, [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], strict=True
        ):
            RollStatistic.create(
                user=1,
                guild=1,
                character=1,
                result=result.name,
                pool=pool,
                difficulty=difficulty,
            )

        # WHEN statistics are pulled for a guild
        p = Statistics(mock_ctx)
        embed = await p.get_embed()

        # THEN confirm the statistics are returned to the user
        assert p.title == "Roll Statistics for guild `Test Guild`"
        assert p.botches == 1
        assert p.successes == 1
        assert p.failures == 1
        assert p.criticals == 1
        assert p.total_rolls == 5
        assert p.average_difficulty == 3
        assert p.average_pool == 3
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*Total Rolls:[ \.]+5.*", regex_flags=re.S)

    @pytest.mark.asyncio()
    async def test_member_statistics(self, mock_ctx, mock_member):
        """Test the pulling user statistics."""
        # GIVEN no statistics in the db
        for record in RollStatistic.select():
            record.delete_instance(recursive=True, delete_nullable=True)

        # WHEN statistics are pulled for a member
        s = Statistics(mock_ctx, user=mock_member)
        embed = await s.get_embed()

        # THEN confirm users are told there are no statistics to display
        assert s.botches == 0
        assert s.successes == 0
        assert s.failures == 0
        assert s.criticals == 0
        assert s.total_rolls == 0
        assert s.average_difficulty == 0
        assert s.average_pool == 0
        assert s.title == "Roll Statistics for `Test User`"
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*No statistics found", regex_flags=re.S)

        # GIVEN rolls in the database
        for result, pool, difficulty in zip(
            RollResultType, [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], strict=True
        ):
            RollStatistic.create(
                user=1,
                guild=1,
                character=1,
                result=result.name,
                pool=pool,
                difficulty=difficulty,
            )

        # WHEN statistics are pulled for a member
        p = Statistics(mock_ctx, user=mock_member)
        embed = await p.get_embed()

        # THEN confirm the statistics are returned to the user
        assert p.title == "Roll Statistics for `Test User`"
        assert p.botches == 1
        assert p.successes == 1
        assert p.failures == 1
        assert p.criticals == 1
        assert p.total_rolls == 5
        assert p.average_difficulty == 3
        assert p.average_pool == 3
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*Total Rolls:[ \.]+5.*", regex_flags=re.S)

    @pytest.mark.asyncio()
    async def test_character_statistics(self, mock_ctx):
        """Test the pulling character statistics."""
        # GIVEN no statistics in the db
        for record in RollStatistic.select():
            record.delete_instance(recursive=True, delete_nullable=True)

        # WHEN statistics are pulled for a character
        s = Statistics(mock_ctx, character=Character.get_by_id(1))
        embed = await s.get_embed()

        # THEN confirm users are told there are no statistics to display
        assert s.botches == 0
        assert s.successes == 0
        assert s.failures == 0
        assert s.criticals == 0
        assert s.total_rolls == 0
        assert s.average_difficulty == 0
        assert s.average_pool == 0
        assert s.title == "Roll Statistics for `Test (Testy) Character`"
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*No statistics found", regex_flags=re.S)

        # GIVEN rolls in the database
        for result, pool, difficulty in zip(
            RollResultType, [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], strict=True
        ):
            RollStatistic.create(
                user=1,
                guild=1,
                character=1,
                result=result.name,
                pool=pool,
                difficulty=difficulty,
            )

        # WHEN statistics are pulled for a character
        p = Statistics(mock_ctx, character=Character.get_by_id(1))
        embed = await p.get_embed()

        # THEN confirm the statistics are returned to the user
        assert p.title == "Roll Statistics for `Test (Testy) Character`"
        assert p.botches == 1
        assert p.successes == 1
        assert p.failures == 1
        assert p.criticals == 1
        assert p.total_rolls == 5
        assert p.average_difficulty == 3
        assert p.average_pool == 3
        assert embed == IsInstance(discord.Embed)
        assert embed.description == IsStr(regex=r".*Total Rolls:[ \.]+5.*", regex_flags=re.S)
