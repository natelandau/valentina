# type: ignore
"""Tests for the dicerolls module."""
from unittest.mock import MagicMock

import pytest

from valentina.models.db_tables import Guild, RollStatistic, User
from valentina.models.dicerolls import DiceRoll, RollResultType
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestDiceRolls:
    """Test Dice Rolling."""

    def test_log_roll_to_db(self, mock_ctx):
        """Test diceroll logging."""
        # SETUP the test with mock objects
        # Create a mock user object
        mock_user = User.get_by_id(1)
        mock_bot = MagicMock()
        mock_bot.user_svc.fetch_user = MagicMock(return_value=mock_user)

        # create a mock guild object
        mock_guild_object = Guild.get_by_id(1)
        mock_guild = MagicMock()
        mock_guild.id = mock_guild_object.id

        # Create a local mock object for ctx
        mock_ctx_local = MagicMock()
        mock_ctx_local.bot = mock_bot
        mock_ctx_local.guild = mock_guild

        # GIVEN a number of logged rolls in the database
        num_logged_rolls = RollStatistic().select().count()

        # WHEN the diceroll is rolled with log_roll set to False and the size of dice is 10
        DiceRoll(mock_ctx, pool=3, dice_size=10, difficulty=6, log_roll=False)

        # THEN assert that the diceroll is not logged
        assert RollStatistic().select().count() == num_logged_rolls

        # WHEN the diceroll is rolled with log_roll set to True and the size of dice is not 10
        DiceRoll(mock_ctx_local, pool=3, dice_size=6, difficulty=6, log_roll=True)

        # THEN assert that the diceroll is not logged
        assert RollStatistic().select().count() == num_logged_rolls

        # WHEN the diceroll is rolled with log_roll set to True and the size of dice is 10
        DiceRoll(mock_ctx_local, pool=3, dice_size=10, difficulty=6, log_roll=True)

        # THEN assert that the diceroll is logged
        assert RollStatistic().select().count() == num_logged_rolls + 1

    def test_roll_exceptions(self, mock_ctx):
        """Ensure that Roll raises exceptions when appropriate.

        GIVEN a call to Roll
        WHEN an argument is invalid
        THEN raise the appropriate exception
        """
        with pytest.raises(errors.ValidationError, match="Pool cannot be less than 0."):
            DiceRoll(mock_ctx, pool=-1)

        with pytest.raises(
            errors.ValidationError, match="Difficulty cannot exceed the size of the dice."
        ):
            DiceRoll(mock_ctx, difficulty=11, pool=1)

        with pytest.raises(errors.ValidationError, match="Pool cannot exceed 100."):
            DiceRoll(mock_ctx, pool=101)

        with pytest.raises(errors.ValidationError, match="Difficulty cannot be less than 0."):
            DiceRoll(mock_ctx, difficulty=-1, pool=1)

        with pytest.raises(errors.ValidationError, match="Invalid dice size"):
            DiceRoll(mock_ctx, difficulty=6, pool=6, dice_size=3)

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
    def test_rolling_dice(self, mock_ctx, pool: int, dice_size: int) -> None:
        """Ensure that the correct number of dice are rolled.

        GIVEN a call to Roll
        WHEN dice are rolled
        THEN assert that the correct number of dice are rolled with the correct dice type.
        """
        for _ in range(100):
            roll = DiceRoll(mock_ctx, pool, dice_size=dice_size, difficulty=1, log_roll=False)
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
        self,
        mock_ctx,
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

        roll = DiceRoll(mock_ctx, pool=3, difficulty=6, log_roll=False)
        assert roll.botches == botches
        assert roll.criticals == criticals
        assert roll.failures == failures
        assert roll.successes == successes
        assert roll.result == result
        assert roll.result_type == result_type

    def test_not_d10(self):
        """Ensure that customizations for non-d10 dice are applied correctly."""
        # SETUP the test with mock objects
        # Create a mock user object
        mock_user = User.get_by_id(1)
        mock_bot = MagicMock()
        mock_bot.user_svc.fetch_user = MagicMock(return_value=mock_user)

        # create a mock guild object
        mock_guild_object = Guild.get_by_id(1)
        mock_guild = MagicMock()
        mock_guild.id = mock_guild_object.id

        # Create a local mock object for ctx
        mock_ctx_local = MagicMock()
        mock_ctx_local.bot = mock_bot
        mock_ctx_local.guild = mock_guild

        # GIVEN a roll with a non-d10 dice
        roll = DiceRoll(mock_ctx_local, pool=3, dice_size=6, difficulty=6, log_roll=True)
        assert roll.result_type == RollResultType.OTHER
