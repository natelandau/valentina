"""Utilities for diceroll probability calculations."""
from collections import defaultdict

import discord
from loguru import logger

from valentina.constants import EmbedColor, RollResultType
from valentina.models.db_tables import RollProbability
from valentina.models.dicerolls import DiceRoll

# Constants for emoji thresholds
SUCCESS_HIGHEST_THRESHOLD = 90
SUCCESS_HIGH_THRESHOLD = 65
SUCCESS_MEDIUM_THRESHOLD = 45
SUCCESS_LOW_THRESHOLD = 15


class Probability:
    """Probability utility class used for generating probabilities of success for different dice rolls."""

    def __init__(
        self, ctx: discord.ApplicationContext, pool: int, difficulty: int, dice_size: int
    ) -> None:
        """Initialize the Probability class.

        Args:
            ctx (discord.ApplicationContext): Context for the discord app.
            pool (int): Pool of dice.
            difficulty (int): Difficulty level.
            dice_size (int): Size of the dice.
        """
        self.ctx = ctx
        self.pool = pool
        self.difficulty = difficulty
        self.dice_size = dice_size
        self.trials = 10000
        self.probabilities = self._calculate()

    def _calculate(self) -> dict[str, float]:
        """Calculate the probability of a given dice roll.

        Returns:
            dict[str, float]: Dictionary containing the calculated probabilities.
        """
        # Return results from the database if they exist
        db_result = RollProbability.get_or_none(
            (RollProbability.pool == self.pool)
            & (RollProbability.difficulty == self.difficulty)
            & (RollProbability.dice_size == self.dice_size)
        )

        if db_result:
            logger.debug("DATABASE: Return probability results")
            return db_result.data

        # Calculate the probabilities
        logger.debug("BOT: Calculate probability results for the given dice roll")
        totals: dict[str, int] = defaultdict(int)
        outcomes: dict[str, int] = defaultdict(int)

        for _ in range(self.trials):
            roll = DiceRoll(
                self.ctx,
                pool=self.pool,
                difficulty=self.difficulty,
                dice_size=self.dice_size,
            )
            totals["total_results"] += roll.result
            totals["botch_dice"] += roll.botches
            totals["success_dice"] += roll.successes
            totals["failure_dice"] += roll.failures
            totals["critical_dice"] += roll.criticals
            outcomes[roll.result_type.value] += 1
            if roll.result_type in (RollResultType.SUCCESS, RollResultType.CRITICAL):
                outcomes["total_successes"] += 1
            if roll.result_type in (RollResultType.FAILURE, RollResultType.BOTCH):
                outcomes["total_failures"] += 1

        probabilities: dict[str, float] = defaultdict(int)
        probabilities["total_results"] = totals["total_results"] / self.trials * 100
        probabilities["botch_dice"] = totals["botch_dice"] / self.trials / self.pool * 100
        probabilities["success_dice"] = totals["success_dice"] / self.trials / self.pool * 100
        probabilities["failure_dice"] = totals["failure_dice"] / self.trials / self.pool * 100
        probabilities["critical_dice"] = totals["critical_dice"] / self.trials / self.pool * 100
        probabilities["total_successes"] = outcomes["total_successes"] / self.trials * 100
        probabilities["total_failures"] = outcomes["total_failures"] / self.trials * 100

        for outcome, frequency in outcomes.items():
            probabilities[outcome] = (frequency / self.trials) * 100

        # Ensure every value exists in the dictionary to prevent bugs in the embed
        for result in RollResultType:
            if result.value not in probabilities:
                probabilities[result.value] = 0

        # Save the results to the database
        logger.debug("DATABASE: Save probability results")
        RollProbability.create(
            pool=self.pool,
            difficulty=self.difficulty,
            dice_size=self.dice_size,
            data=probabilities,
        )

        return probabilities

    def _get_description(self) -> str:
        """Return the probability description.

        Returns:
            str: Probability description for use in the embed.
        """
        if self.probabilities["total_successes"] >= SUCCESS_HIGHEST_THRESHOLD:
            emoji = "🎉🎊"
        elif self.probabilities["total_successes"] >= SUCCESS_HIGH_THRESHOLD:
            emoji = "👍"
        elif self.probabilities["total_successes"] >= SUCCESS_MEDIUM_THRESHOLD:
            emoji = "🤷‍♂️"
        elif self.probabilities["total_successes"] <= SUCCESS_LOW_THRESHOLD:
            emoji = "💀"
        else:
            emoji = "👎"

        return f"""\
## Overall success probability: {self.probabilities['total_successes']:.2f}% {emoji}

Rolling `{self.pool}d{self.dice_size}` against difficulty `{self.difficulty}`

### Roll Result Probabilities
*(Chance that any specific roll will come up with the specified result)*
```python
Critical Success:  {self.probabilities[RollResultType.CRITICAL.value]:.2f}%
Success:           {self.probabilities[RollResultType.SUCCESS.value]:.2f}%
Failure:           {self.probabilities[RollResultType.FAILURE.value]:.2f}%
Botch:             {self.probabilities[RollResultType.BOTCH.value]:.2f}%
```
### Dice Value Probabilities
*(Chance that any specific die will come up with the specified value)*
```python
Critical Success (10):  {self.probabilities['critical_dice']:.2f}%
Success (>= {self.difficulty}):         {self.probabilities['success_dice']:.2f}%
Failure (< {self.difficulty}):          {self.probabilities['failure_dice']:.2f}%
Botch (1):              {self.probabilities['botch_dice']:.2f}%
```

> DEFINITIONS:
> - _Critical Success_: More successes than dice rolled
> - _Success_: At least one success after all dice are tallied
> - _Failure_: Zero successes after all dice are tallied
> - _Botch_: Negative successes after all dice are tallied
        """

    async def get_embed(self) -> discord.Embed:
        """Return the probability embed.

        Returns:
            discord.Embed: Embed object containing the probability statistics.
        """
        embed = discord.Embed(
            title="",
            color=EmbedColor.INFO.value,
        )
        embed.description = self._get_description()
        embed.set_footer(text=f"Probabilities based on {self.trials:,} trials")

        return embed
