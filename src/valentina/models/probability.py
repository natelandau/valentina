"""Utilities for diceroll probability calculations."""

from collections import defaultdict
from datetime import datetime

import discord
from beanie import Document, Indexed
from loguru import logger
from pydantic import Field

from valentina.constants import EmbedColor, RollResultType
from valentina.models.dicerolls import DiceRoll
from valentina.utils.helpers import time_now

# Constants for emoji thresholds
SUCCESS_HIGHEST_THRESHOLD = 90
SUCCESS_HIGH_THRESHOLD = 65
SUCCESS_MEDIUM_THRESHOLD = 45
SUCCESS_LOW_THRESHOLD = 15


class RollProbability(Document):
    """Represents a roll probability in the database."""

    # Metadata
    pool: Indexed(int)  # type: ignore [valid-type]
    difficulty: Indexed(int)  # type: ignore [valid-type]
    dice_size: Indexed(int)  # type: ignore [valid-type]
    created: datetime = Field(default_factory=time_now)

    # Results
    total_results: float
    botch_dice: float
    success_dice: float
    failure_dice: float
    critical_dice: float
    total_successes: float
    total_failures: float
    # The name of each value in the RollResultType enum
    BOTCH: float
    CRITICAL: float
    FAILURE: float
    SUCCESS: float
    OTHER: float


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

    async def _calculate(self) -> RollProbability:
        """Calculate the probability of a given dice roll.

        Returns:
            RollProbability: RollProbability object containing the results.
        """
        # Return results from the database if they exist
        db_result = await RollProbability.find(
            RollProbability.pool == self.pool,
            RollProbability.difficulty == self.difficulty,
            RollProbability.dice_size == self.dice_size,
        ).first_or_none()

        if db_result:
            logger.debug("DATABASE: Return probability results")
            return db_result

        # Calculate the probabilities
        logger.debug("BOT: Calculate probability results for the given dice roll")

        total_results = 0
        botch_dice = 0
        success_dice = 0
        failure_dice = 0
        critical_dice = 0
        total_successes = 0
        total_failures = 0
        result_counts = {result: 0 for result in RollResultType}

        for _ in range(self.trials):
            roll = DiceRoll(
                self.ctx,
                pool=self.pool,
                difficulty=self.difficulty,
                dice_size=self.dice_size,
            )
            total_results += roll.result
            botch_dice += roll.botches
            success_dice += roll.successes
            failure_dice += roll.failures
            critical_dice += roll.criticals
            result_counts[roll.result_type] += 1

            if roll.result_type in {RollResultType.SUCCESS, RollResultType.CRITICAL}:
                total_successes += 1
            if roll.result_type in {RollResultType.FAILURE, RollResultType.BOTCH}:
                total_failures += 1

        probabilities: dict[str, float] = defaultdict(int)
        probabilities["total_results"] = total_results / self.trials * 100
        probabilities["botch_dice"] = botch_dice / self.trials / self.pool * 100
        probabilities["success_dice"] = success_dice / self.trials / self.pool * 100
        probabilities["failure_dice"] = failure_dice / self.trials / self.pool * 100
        probabilities["critical_dice"] = critical_dice / self.trials / self.pool * 100
        probabilities["total_successes"] = total_successes / self.trials * 100
        probabilities["total_failures"] = total_failures / self.trials * 100

        for outcome, frequency in result_counts.items():
            probabilities[outcome.name] = (frequency / self.trials) * 100

        # Ensure every value exists in the dictionary to prevent bugs in the embed
        for result in RollResultType:
            if result.name not in probabilities:
                probabilities[result.name] = 0

        # Save the results to the database
        logger.debug("DATABASE: Save probability results")
        probabilities = RollProbability(
            pool=self.pool,
            difficulty=self.difficulty,
            dice_size=self.dice_size,
            total_results=probabilities["total_results"],
            botch_dice=probabilities["botch_dice"],
            success_dice=probabilities["success_dice"],
            failure_dice=probabilities["failure_dice"],
            critical_dice=probabilities["critical_dice"],
            total_successes=probabilities["total_successes"],
            total_failures=probabilities["total_failures"],
            # The name of each value in the RollResultType enum
            BOTCH=probabilities["BOTCH"],
            CRITICAL=probabilities["CRITICAL"],
            FAILURE=probabilities["FAILURE"],
            SUCCESS=probabilities["SUCCESS"],
            OTHER=probabilities["OTHER"],
        )
        await probabilities.insert()
        return probabilities

    def _get_description(self, results: RollProbability) -> str:
        """Return the probability description.

        Args:
            results (RollProbability): RollProbability object containing the results.

        Returns:
            str: Probability description for use in the embed.
        """
        if results.total_successes >= SUCCESS_HIGHEST_THRESHOLD:
            emoji = "🎉🎊"
        elif results.total_successes >= SUCCESS_HIGH_THRESHOLD:
            emoji = "👍"
        elif results.total_successes >= SUCCESS_MEDIUM_THRESHOLD:
            emoji = "🤷‍♂️"
        elif results.total_successes <= SUCCESS_LOW_THRESHOLD:
            emoji = "💀"
        else:
            emoji = "👎"

        return f"""\
## Overall success probability: {results.total_successes:.2f}% {emoji}

Rolling `{self.pool}d{self.dice_size}` against difficulty `{self.difficulty}`

### Roll Result Probabilities
*(Chance that any specific roll will come up with the specified result)*
```python
Critical Success:  {results.CRITICAL:.2f}%
         Success:  {results.SUCCESS:.2f}%
         Failure:  {results.FAILURE:.2f}%
           Botch:  {results.BOTCH:.2f}%
```
### Dice Value Probabilities
*(Chance that any specific die will come up with the specified value)*
```python
 Critical (10):  {results.critical_dice:.2f}%
Success (>= {self.difficulty}):  {results.success_dice:.2f}%
 Failure (< {self.difficulty}):  {results.failure_dice:.2f}%
     Botch (1):  {results.botch_dice:.2f}%
```

> - Probabilities based on {self.trials:,} trials
> - Definitions
>  - _Critical Success_: More successes than dice rolled
>  - _Success_: At least one success after all dice are tallied
>  - _Failure_: Zero successes after all dice are tallied
>  - _Botch_: Negative successes after all dice are tallied


        """

    async def get_embed(self) -> discord.Embed:
        """Return the probability embed.

        Returns:
            discord.Embed: Embed object containing the probability statistics.
        """
        result = await self._calculate()
        description = self._get_description(result)

        embed = discord.Embed(
            title="",
            color=EmbedColor.INFO.value,
        )
        embed.description = description
        embed.set_footer(
            text=f"Requested by {self.ctx.author}",
            icon_url=self.ctx.author.display_avatar.url,
        )

        return embed
