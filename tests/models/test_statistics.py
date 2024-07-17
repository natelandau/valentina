# type: ignore
"""Test the Statistics module."""

import discord
import pytest
from tests.factories import *

from valentina.constants import RollResultType
from valentina.models import RollStatistic, Statistics


@pytest.mark.drop_db()
async def test_guild_statistics_no_results(mock_ctx1):
    """Test pulling guild statistics."""
    # GIVEN a guild with no statistics
    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.guild_statistics()

    # THEN confirm no statistics are returned
    assert s.botches == 0
    assert s.successes == 0
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 0
    assert s.average_difficulty == 0
    assert s.average_pool == 0
    assert result == "\n## Roll statistics for guild `Test Guild`\nNo statistics found"


@pytest.mark.drop_db()
async def test_guild_statistics_results(mock_ctx1):
    """Test pulling guild statistics."""
    # GIVEN a guild with statistics
    stat1 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.SUCCESS,
        pool=1,
        difficulty=1,
    )
    stat2 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=3,
    )
    stat3 = RollStatistic(
        user=2,
        guild=2,
        character="2",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=1,
    )
    await stat1.insert()
    await stat2.insert()
    await stat3.insert()

    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.guild_statistics(as_embed=True)

    # THEN confirm the statistics are returned to the user
    assert s.botches == 1
    assert s.successes == 1
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 2
    assert s.average_difficulty == 2
    assert isinstance(result, discord.Embed)
    assert "Successful Rolls ........ 1   (50.00%)" in result.description


@pytest.mark.drop_db()
async def test_user_statistics_no_results(mock_ctx1):
    """Test pulling user statistics."""
    # GIVEN a user with no statistics
    # WHEN statistics are pulled for a user
    s = Statistics(mock_ctx1)
    result = await s.user_statistics(mock_ctx1.author, with_title=False)

    # THEN confirm no statistics are returned
    assert s.botches == 0
    assert s.successes == 0
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 0
    assert s.average_difficulty == 0
    assert s.average_pool == 0
    assert result == "\nNo statistics found"


@pytest.mark.drop_db()
async def test_user_statistics_results(mock_ctx1):
    """Test pulling user statistics."""
    # GIVEN a user with statistics
    stat1 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.SUCCESS,
        pool=1,
        difficulty=1,
    )
    stat2 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=3,
    )
    stat3 = RollStatistic(
        user=2,
        guild=2,
        character="2",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=1,
    )
    await stat1.insert()
    await stat2.insert()
    await stat3.insert()

    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.user_statistics(mock_ctx1.author, as_embed=True, with_help=False)

    # THEN confirm the statistics are returned to the user
    assert s.botches == 1
    assert s.successes == 1
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 2
    assert s.average_difficulty == 2
    assert isinstance(result, discord.Embed)
    assert "Successful Rolls ........ 1   (50.00%)" in result.description
    assert "Definitions:" not in result.description


@pytest.mark.drop_db()
async def test_character_statistics_no_results(mock_ctx1, character_factory):
    """Test pulling character_statistics."""
    # GIVEN a character with no statistics
    character = character_factory.build()

    # WHEN statistics are pulled for a character
    s = Statistics(mock_ctx1)
    result = await s.character_statistics(character, with_title=False)

    # THEN confirm no statistics are returned
    assert s.botches == 0
    assert s.successes == 0
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 0
    assert s.average_difficulty == 0
    assert s.average_pool == 0
    assert result == "\nNo statistics found"


async def test_character_statistics_results(mock_ctx1, character_factory):
    """Test pulling character_statistics."""
    # GIVEN a character with statistics
    character = character_factory.build()
    stat1 = RollStatistic(
        user=1,
        guild=1,
        character=str(character.id),
        result=RollResultType.SUCCESS,
        pool=1,
        difficulty=1,
    )
    stat2 = RollStatistic(
        user=1,
        guild=1,
        character=str(character.id),
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=3,
    )
    stat3 = RollStatistic(
        user=2,
        guild=2,
        character="not_for_this_character",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=1,
    )
    await stat1.insert()
    await stat2.insert()
    await stat3.insert()

    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.character_statistics(character, as_embed=True, with_help=False)

    # THEN confirm the statistics are returned to the user
    assert s.botches == 1
    assert s.successes == 1
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 2
    assert s.average_difficulty == 2
    assert isinstance(result, discord.Embed)
    assert "Successful Rolls ........ 1   (50.00%)" in result.description
    assert "Definitions:" not in result.description


async def test_campaign_statistics_results(mock_ctx1, character_factory, campaign_factory):
    """Test pulling character_statistics."""
    # GIVEN a character with statistics
    campaign = campaign_factory.build()
    character = character_factory.build()
    stat1 = RollStatistic(
        user=1,
        guild=1,
        character=str(character.id),
        result=RollResultType.SUCCESS,
        pool=1,
        difficulty=1,
        campaign=str(campaign.id),
    )
    stat2 = RollStatistic(
        user=1,
        guild=1,
        character=str(character.id),
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=3,
        campaign=str(campaign.id),
    )
    stat3 = RollStatistic(
        user=2,
        guild=2,
        character="not_for_this_character",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=1,
        campaign=str(campaign.id),
    )
    await stat1.insert()
    await stat2.insert()
    await stat3.insert()

    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.campaign_statistics(campaign, as_embed=True, with_help=False)

    # THEN confirm the statistics are returned to the user
    assert s.botches == 2
    assert s.successes == 1
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 3
    assert s.average_difficulty == 2
    assert isinstance(result, discord.Embed)
    assert "Successful Rolls ........ 1   (33.33%)" in result.description
    assert "Definitions:" not in result.description


@pytest.mark.drop_db()
async def test_guild_statistics_results_json(mock_ctx1):
    """Test pulling guild statistics as a json object."""
    # GIVEN a guild with statistics
    stat1 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.SUCCESS,
        pool=1,
        difficulty=1,
    )
    stat2 = RollStatistic(
        user=1,
        guild=1,
        character="1",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=3,
    )
    stat3 = RollStatistic(
        user=2,
        guild=2,
        character="2",
        result=RollResultType.BOTCH,
        pool=1,
        difficulty=1,
    )
    await stat1.insert()
    await stat2.insert()
    await stat3.insert()

    # WHEN statistics are pulled for a guild
    s = Statistics(mock_ctx1)
    result = await s.guild_statistics(as_json=True)

    # THEN confirm the statistics are returned to the user
    assert s.botches == 1
    assert s.successes == 1
    assert s.failures == 0
    assert s.criticals == 0
    assert s.total_rolls == 2
    assert s.average_difficulty == 2
    assert result == {
        "average_difficulty": "2",
        "average_pool": "1",
        "botches": "1",
        "botches_percentage": "50.00",
        "criticals": "0",
        "criticals_percentage": "0.00",
        "failures": "0",
        "failures_percentage": "0.00",
        "successes": "1",
        "successes_percentage": "50.00",
        "total_rolls": "2",
    }
