# type: ignore
"""Tests for the probability module."""
import re

import discord
import pytest
from rich import print

from valentina.models import Probability, RollProbability

from .helpers import Regex


async def test_calculate_no_db(mock_ctx1):
    """Test the calculate method."""
    # GIVEN an empty RollProbability collection
    # WHEN calculating the probability of a roll
    p = Probability(mock_ctx1, pool=5, difficulty=6, dice_size=10)
    result = await p._calculate()

    # THEN confirm the probability is correct and the result is saved to the database
    assert result == await RollProbability.find_one()
    assert result.pool == 5
    assert result.difficulty == 6
    assert result.dice_size == 10
    assert round(result.total_results) in range(195, 210)
    assert round(result.botch_dice) in range(5, 15)
    assert round(result.success_dice) in range(35, 45)
    assert round(result.failure_dice) in range(35, 45)
    assert round(result.critical_dice) in range(5, 15)
    assert round(result.total_successes) in range(70, 80)
    assert round(result.total_failures) in range(15, 30)
    assert round(result.BOTCH) in range(13, 17)
    assert round(result.FAILURE) in range(8, 14)
    assert round(result.SUCCESS) in range(70, 73)
    assert round(result.CRITICAL) in range(3, 6)


@pytest.mark.drop_db()
async def test_calculate_with_db(mock_ctx1):
    """Test the calculate method."""
    # GIVEN a RollProbability collection with a result
    r = RollProbability(
        pool=5,
        difficulty=6,
        dice_size=10,
        total_results=200.31,
        botch_dice=9.99,
        success_dice=39.722,
        failure_dice=40.128,
        critical_dice=10.16,
        total_successes=75.77000000000001,
        total_failures=24.23,
        BOTCH=13.459999999999999,
        CRITICAL=4.390000000000001,
        FAILURE=10.77,
        SUCCESS=71.38,
        OTHER=0.0,
    )
    await r.insert()

    # WHEN calculating the probability of a roll
    p = Probability(mock_ctx1, pool=5, difficulty=6, dice_size=10)
    result = await p._calculate()

    # THEN confirm the probability is correct and the result pulled from the database
    db_result = await RollProbability.find_one()
    assert await RollProbability.find_all().count() == 1
    assert result.id == db_result.id


async def test_get_description(mock_ctx1):
    """Test the _get_description method."""
    # Given a roll result
    obj = RollProbability(
        pool=5,
        difficulty=6,
        dice_size=10,
        total_results=200.31,
        botch_dice=9.99,
        success_dice=39.722,
        failure_dice=40.128,
        critical_dice=10.16,
        total_successes=75.77000000000001,
        total_failures=24.23,
        BOTCH=13.459999999999999,
        CRITICAL=4.390000000000001,
        FAILURE=10.77,
        SUCCESS=71.38,
        OTHER=0.0,
    )

    # WHEN getting the description
    p = Probability(mock_ctx1, pool=5, difficulty=6, dice_size=10)
    result = p._get_description(results=obj)

    # THEN confirm the description is correct
    assert result == Regex(r"## Overall success probability: \d{2}\.\d{2}% 👍", re.I)
    assert "Rolling `5d10` against difficulty `6`" in result


async def test_get_embed(mock_ctx1):
    """Test the get_embed method."""
    # GIVEN a probability instance
    p = Probability(mock_ctx1, pool=5, difficulty=6, dice_size=10)

    # WHEN getting the embed
    embed = await p.get_embed()

    # THEN confirm the embed is correct
    assert isinstance(embed, discord.Embed)
    assert embed.description == Regex(r"## Overall success probability: \d{2}\.\d{2}% 👍", re.I)
    assert "Rolling `5d10` against difficulty `6`" in embed.description
