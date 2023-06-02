"""Models for dice rolls."""

from numpy.random import default_rng

from valentina.models.enums import DiceType

_rng = default_rng()
_max_pool_size = 100


class Roll:
    """A container class that determines the result of a roll.

    Dice rolling mechanics are based on our unique system, which is loosely based on the Storyteller system. The following rules apply only to throws of 10 sided dice.

    * A roll is made up of a pool of dice, which is the total number of dice rolled.
    * The difficulty is the number that must be rolled on the dice to count as a success.
    * The dice type is the type of dice rolled. (Default is a d10.)
    * Ones negate two successes
    * Tens count as two successes
    * Ones and tens cancel each other out
    * A botch occurs when the result of all dice is less than 0
    * A critical occurs when the roll is a success and the number of 10s rolled is greater than half the pool
    * A failure occurs when the number of dice rolled above the difficulty is zero after accounting for cancelling ones and tens
    * A success occurs when the number of dice rolled above the difficulty is greater than zero after accounting for cancelling ones and tens
    * The result of a roll is the number of successes after accounting for botches and cancelling ones and tens

    Attributes:
        botches (int): The number of ones in the dice.
        criticals (int): The number of rolled criticals (Highest number on dice).
        dice_type (DiceType): The type of dice to roll.
        difficulty (int): The difficulty of the roll.
        embed_color (int): The color of the embed.
        failures (int): The number of unsuccessful dice not including botches.
        is_botch (bool): Whether the roll is a botch.
        is_critical (bool): Whether the roll is a critical success.
        is_failure (bool): Whether the roll is a failure.
        is_success (bool): Whether the roll is a success.
        main_takeaway (str): The roll's main takeaway - i.e. "SUCCESS", "FAILURE", etc.
        pool (int): The pool's total size, including hunger.
        result (int): The number of successes after accounting for botches and cancelling ones and tens.
        roll (list[int]): A list of the result all rolled dice.
        successes (int): The number of successful dice not including criticals.

    """

    def __init__(self, pool: int, difficulty: int = 6, dice_type: DiceType = DiceType.D10):
        """A container class that determines the result of a roll.

        Args:
            pool (int): The pool's total size, including hunger
            difficulty (int, optional): The difficulty of the roll. Defaults to 6.
            dice_type (DiceType, optional): The type of dice to roll. Defaults to DiceType.D10.
        """
        if difficulty < 0:
            raise ValueError(f"Difficulty cannot be less than 0. (Got `{difficulty}`.)")
        if difficulty > dice_type.value:
            raise ValueError(
                f"Difficulty cannot exceed the size of the dice. (Got `{difficulty}` for `{dice_type.name}`.)"
            )
        if pool < 0:
            raise ValueError(f"Pool cannot be less than 0. (Got `{pool}`.)")
        if pool > _max_pool_size:
            raise ValueError(f"Pool cannot exceed {_max_pool_size}. (Got `{pool}`.)")

        self.difficulty = difficulty
        self.pool = pool
        self.dice_type = dice_type

    @property
    def roll(self) -> list[int]:
        """Roll the dice and return the results."""
        return list(map(int, _rng.integers(1, self.dice_type.value + 1, self.pool)))

    @property
    def botches(self) -> int:
        """Retrieve the number of ones in the dice."""
        return self.roll.count(1)

    @property
    def criticals(self) -> int:
        """Retrieve the number of rolled criticals (Highest number on dice)."""
        return self.roll.count(self.dice_type.value)

    @property
    def failures(self) -> int:
        """Retrieve the number of unsuccessful dice not including botches."""
        count = 0
        for die in self.roll:
            if 2 <= die <= self.difficulty - 1:  # noqa: PLR2004
                count += 1
        return count

    @property
    def successes(self) -> int:
        """Retrieve the total number of dice which beat the difficulty not including criticals."""
        count = 0
        for die in self.roll:
            if self.difficulty <= die <= self.dice_type.value - 1:
                count += 1
        return count

    @property
    def result(self) -> int:
        """Retrieve the number of successes to count."""
        if self.dice_type != DiceType.D10:
            return self.successes + self.criticals - self.failures - self.botches

        botches = self.botches - self.criticals
        botches = botches if botches > 0 else 0
        criticals = self.criticals - self.botches
        criticals = criticals if criticals > 0 else 0

        return self.successes + (criticals * 2) - (botches * 2)

    @property
    def is_botch(self) -> bool:
        """Determine if the roll is a botch."""
        if self.result < 0:
            return True
        return False

    @property
    def is_failure(self) -> bool:
        """Determine if the roll is a botch."""
        if self.result <= 0:
            return True
        return False

    @property
    def is_success(self) -> bool:
        """Determine if the roll is a success."""
        if self.result > 0:
            return True
        return False

    @property
    def is_critical(self) -> bool:
        """Determine if the roll is a critical success (greater than half the pool are 10s)."""
        if not self.is_botch and self.criticals >= (self.pool / 2):
            return True
        return False

    @property
    def embed_color(self) -> int:
        """Determine the Discord embed color based on the result of the roll."""
        if self.dice_type != DiceType.D10:
            return 0xEA3323  # Red-orange

        if self.is_botch:
            return 0x000000  # Black
        if self.is_critical:
            return 0x00FF00  # Green
        if self.is_success:
            return 0x7777FF  # Blurple-ish
        if self.is_failure:
            return 0x808080  # Gray

        return None

    @property
    def main_takeaway(self) -> str:
        """The roll's main takeaway--i.e. "SUCCESS", "FAILURE", etc."""
        if self.dice_type != DiceType.D10:
            return "Result"

        if self.is_botch:
            return "Botch"
        if self.is_critical:
            return "Critical Success"
        if self.is_success:
            return "Success"
        if self.is_failure:
            return "Failure"

        return None
