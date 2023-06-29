# type: ignore
"""Tests for the dicerolls module."""
import pytest

from valentina.models.dicerolls import DiceRoll


def test_roll_exceptions():
    """Ensure that Roll raises exceptions when appropriate.

    GIVEN a call to Roll
    WHEN an argument is invalid
    THEN raise the appropriate exception
    """
    with pytest.raises(ValueError, match="Pool cannot be less than 0."):
        DiceRoll(pool=-1)

    with pytest.raises(ValueError, match="Difficulty cannot exceed the size of the dice."):
        DiceRoll(difficulty=11, pool=1)

    with pytest.raises(ValueError, match="Pool cannot exceed 100."):
        DiceRoll(pool=101)

    with pytest.raises(ValueError, match="Difficulty cannot be less than 0."):
        DiceRoll(difficulty=-1, pool=1)

    with pytest.raises(ValueError, match="Invalid dice size"):
        DiceRoll(difficulty=6, pool=6, dice_size=3)


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
def test_rolling_dice(pool: int, dice_size: int) -> None:
    """Ensure that the correct number of dice are rolled.

    GIVEN a call to Roll
    WHEN dice are rolled
    THEN assert that the correct number of dice are rolled with the correct dice type.
    """
    for _ in range(100):
        roll = DiceRoll(pool, dice_size=dice_size, difficulty=1)
        assert len(roll.roll) == pool
        assert all(1 <= die <= dice_size for die in roll.roll)


@pytest.mark.parametrize(
    (
        "roll",
        "botches",
        "criticals",
        "failures",
        "successes",
        "result",
        "is_botch",
        "is_failure",
        "is_success",
        "is_critical",
    ),
    [
        ([1, 2, 3], 1, 0, 2, 0, -2, True, False, False, False),
        ([10, 10, 10], 0, 3, 0, 0, 6, False, False, True, True),
        ([2, 3, 2], 0, 0, 3, 0, 0, False, True, False, False),
        ([6, 7, 8], 0, 0, 0, 3, 3, False, False, True, False),
        ([2, 2, 7, 7], 0, 0, 2, 2, 2, False, False, True, False),
        ([1, 2, 7, 7], 1, 0, 1, 2, 0, False, True, False, False),
        ([1, 1, 7, 7], 2, 0, 0, 2, -2, True, False, False, False),
        ([2, 7, 10], 0, 1, 1, 1, 3, False, False, True, False),
        ([2, 10, 10], 0, 2, 1, 0, 4, False, False, True, True),
        ([1, 2, 3, 10], 1, 1, 2, 0, 0, False, True, False, False),
        ([1, 1, 3, 10], 2, 1, 1, 0, -2, True, False, False, False),
        ([1, 1, 3, 7, 8, 10], 2, 1, 1, 2, 0, False, True, False, False),
        ([1, 1, 3, 7, 7, 8, 10], 2, 1, 1, 3, 1, False, False, True, False),
    ],
)
def test_roll_successes(
    mocker,
    roll,
    botches,
    criticals,
    failures,
    result,
    successes,
    is_botch,
    is_failure,
    is_success,
    is_critical,
) -> None:
    """Ensure that successes are calculated correctly.

    GIVEN a call to Roll
    WHEN successes are calculated
    THEN assert that the correct number of successes are calculated.
    """
    mocker.patch.object(DiceRoll, "roll", roll)

    roll = DiceRoll(pool=3, difficulty=6)
    assert roll.botches == botches
    assert roll.criticals == criticals
    assert roll.failures == failures
    assert roll.successes == successes
    assert roll.result == result
    assert roll.is_botch == is_botch
    assert roll.is_failure == is_failure
    assert roll.is_success == is_success
    assert roll.is_critical == is_critical
