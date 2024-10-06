# type: ignore
"""Tests for the dicerolls module."""

import pytest

from valentina.constants import RollResultType
from valentina.models import DiceRoll, RollStatistic
from valentina.utils import errors


@pytest.mark.no_db
@pytest.mark.parametrize(
    ("guild_id", "author_id", "author_name"), [(None, 1, "name"), (1, None, "name"), (1, 1, None)]
)
def test_fail_without_init_data(guild_id, author_id, author_name) -> None:
    """Ensure that Roll fails without the required data.

    GIVEN a call to Roll
    WHEN the required data is not provided
    THEN raise an exception
    """
    with pytest.raises(errors.ValidationError):
        DiceRoll(guild_id=guild_id, author_id=author_id, author_name=author_name, pool=1)


@pytest.mark.no_db
@pytest.mark.parametrize(
    (
        "pool",
        "dice_size",
    ),
    [
        (10, 10),
        (3, 6),
        (7, 4),
        (5, 100),
    ],
)
def test_rolling_dice(mock_ctx1, pool: int, dice_size: int) -> None:
    """Ensure that the correct number of dice are rolled.

    GIVEN a call to Roll
    WHEN dice are rolled
    THEN assert that the correct number of dice are rolled with the correct dice type.
    """
    for _ in range(100):
        roll = DiceRoll(pool=pool, ctx=mock_ctx1, dice_size=dice_size, difficulty=1)
        assert len(roll.roll) == pool
        assert all(1 <= die <= dice_size for die in roll.roll)


@pytest.mark.no_db
@pytest.mark.parametrize(
    (
        "roll",
        "botches",
        "criticals",
        "failures",
        "successes",
        "result",
        "result_type",
    ),
    [
        ([1, 2, 3], 1, 0, 2, 0, -2, RollResultType.BOTCH),
        ([10, 10, 10], 0, 3, 0, 0, 6, RollResultType.CRITICAL),
        ([2, 3, 2], 0, 0, 3, 0, 0, RollResultType.FAILURE),
        ([6, 7, 8], 0, 0, 0, 3, 3, RollResultType.SUCCESS),
        ([2, 2, 7, 7], 0, 0, 2, 2, 2, RollResultType.SUCCESS),
        ([1, 2, 7, 7], 1, 0, 1, 2, 0, RollResultType.FAILURE),
        ([1, 1, 7, 7], 2, 0, 0, 2, -2, RollResultType.BOTCH),
        ([2, 7, 10], 0, 1, 1, 1, 3, RollResultType.SUCCESS),
        ([2, 10, 10], 0, 2, 1, 0, 4, RollResultType.CRITICAL),
        ([1, 2, 3, 10], 1, 1, 2, 0, 0, RollResultType.FAILURE),
        ([1, 1, 3, 10], 2, 1, 1, 0, -2, RollResultType.BOTCH),
        ([1, 1, 3, 7, 8, 10], 2, 1, 1, 2, 0, RollResultType.FAILURE),
        ([1, 1, 3, 7, 7, 8, 10], 2, 1, 1, 3, 1, RollResultType.SUCCESS),
    ],
)
def test_roll_successes(
    mock_ctx1,
    mocker,
    roll,
    botches,
    criticals,
    failures,
    successes,
    result,
    result_type,
) -> None:
    """Ensure that successes are calculated correctly.

    GIVEN a call to Roll
    WHEN successes are calculated
    THEN assert that the correct number of successes are calculated.
    """
    mocker.patch.object(DiceRoll, "roll", roll)

    roll = DiceRoll(pool=3, ctx=mock_ctx1, difficulty=6)
    assert roll.botches == botches
    assert roll.criticals == criticals
    assert roll.failures == failures
    assert roll.successes == successes
    assert roll.result == result
    assert roll.result_type == result_type


@pytest.mark.no_db
async def test_not_d10(mock_ctx1):
    """Ensure that customizations for non-d10 dice are applied correctly."""
    # GIVEN a roll with a non-d10 dice
    roll = DiceRoll(ctx=mock_ctx1, pool=3, dice_size=6, difficulty=6)
    assert roll.result_type == RollResultType.OTHER


@pytest.mark.no_db
def test_roll_exceptions(mock_ctx1):
    """Ensure that Roll raises exceptions when appropriate.

    GIVEN a call to Roll
    WHEN an argument is invalid
    THEN raise the appropriate exception
    """
    with pytest.raises(errors.ValidationError, match="Pool cannot be less than 0."):
        DiceRoll(ctx=mock_ctx1, pool=-1)

    with pytest.raises(
        errors.ValidationError, match="Difficulty cannot exceed the size of the dice."
    ):
        DiceRoll(ctx=mock_ctx1, difficulty=11, pool=1)

    with pytest.raises(errors.ValidationError, match="Pool cannot exceed 100."):
        DiceRoll(ctx=mock_ctx1, pool=101)

    with pytest.raises(errors.ValidationError, match="Difficulty cannot be less than 0."):
        DiceRoll(ctx=mock_ctx1, difficulty=-1, pool=1)

    with pytest.raises(errors.ValidationError, match="Invalid dice size"):
        DiceRoll(ctx=mock_ctx1, difficulty=6, pool=6, dice_size=3)


@pytest.mark.drop_db
async def test_log_roll(mock_ctx1):
    """Test diceroll logging to the database."""
    # GIVEN a diceroll object and a list of two traits
    d = DiceRoll(ctx=mock_ctx1, pool=3, dice_size=10, difficulty=6)
    traits = ["test_trait1", "test_trait2"]

    # WHEN the log_roll method is called
    await d.log_roll(traits)

    # THEN assert that the diceroll is logged
    assert await RollStatistic.find_all().count() == 1
    db_result = await RollStatistic.find_one()
    assert db_result.pool == 3
    assert db_result.difficulty == 6
    assert db_result.traits == ["test_trait1", "test_trait2"]
