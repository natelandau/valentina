"""Models for dice rolls."""

from numpy.random import default_rng

from valentina.models.constants import DiceType

_rng = default_rng()
_max_pool_size = 100


class DiceRoll:
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
        takeaway (str): The roll's main takeaway - i.e. "SUCCESS", "FAILURE", etc.
        pool (int): The pool's total size, including hunger.
        result (int): The number of successes after accounting for botches and cancelling ones and tens.
        roll (list[int]): A list of the result all rolled dice.
        successes (int): The number of successful dice not including criticals.

    """

    def __init__(self, pool: int, difficulty: int = 6, dice_size: int = 10) -> None:
        """A container class that determines the result of a roll.

        Args:
            dice_size (int, optional): The size of the dice. Defaults to 10.
            difficulty (int, optional): The difficulty of the roll. Defaults to 6.
            pool (int): The pool's total size, including hunger
        """
        dice_size_values = [member.value for member in DiceType]
        if dice_size not in dice_size_values:
            raise ValueError(f"Invalid dice size `{dice_size}`.")

        self.dice_type = DiceType(dice_size)

        if difficulty < 0:
            raise ValueError(f"Difficulty cannot be less than 0. (Got `{difficulty}`.)")
        if difficulty > self.dice_type.value:
            raise ValueError(
                f"Difficulty cannot exceed the size of the dice. (Got `{difficulty}` for `{self.dice_type.name}`.)"
            )
        if pool < 0:
            raise ValueError(f"Pool cannot be less than 0. (Got `{pool}`.)")
        if pool > _max_pool_size:
            raise ValueError(f"Pool cannot exceed {_max_pool_size}. (Got `{pool}`.)")

        self.difficulty = difficulty
        self.pool = pool
        self._roll: list[int] = None
        self._botches: int = None
        self._criticals: int = None
        self._failures: int = None
        self._successes: int = None
        self._result: int = None

    @property
    def roll(self) -> list[int]:
        """Roll the dice and return the results."""
        if not self._roll:
            self._roll = list(map(int, _rng.integers(1, self.dice_type.value + 1, self.pool)))

        return self._roll

    @property
    def botches(self) -> int:
        """Retrieve the number of ones in the dice."""
        if not self._botches:
            self._botches = self.roll.count(1)
        return self._botches

    @property
    def criticals(self) -> int:
        """Retrieve the number of rolled criticals (Highest number on dice)."""
        if not self._criticals:
            self._criticals = self.roll.count(self.dice_type.value)
        return self._criticals

    @property
    def failures(self) -> int:
        """Retrieve the number of unsuccessful dice not including botches."""
        if not self._failures:
            count = 0
            for die in self.roll:
                if 2 <= die <= self.difficulty - 1:  # noqa: PLR2004
                    count += 1
            self._failures = count
        return self._failures

    @property
    def successes(self) -> int:
        """Retrieve the total number of dice which beat the difficulty not including criticals."""
        if not self._successes:
            count = 0
            for die in self.roll:
                if self.difficulty <= die <= self.dice_type.value - 1:
                    count += 1
            self._successes = count
        return self._successes

    @property
    def result(self) -> int:
        """Retrieve the number of successes to count."""
        if not self._result:
            if self.dice_type != DiceType.D10:
                self._result = self.successes + self.criticals - self.failures - self.botches
            else:
                botches = self.botches - self.criticals
                botches = botches if botches > 0 else 0
                criticals = self.criticals - self.botches
                criticals = criticals if criticals > 0 else 0

                self._result = self.successes + (criticals * 2) - (botches * 2)

        return self._result

    @property
    def is_botch(self) -> bool:
        """Determine if the roll is a botch."""
        if self.result >= 0:
            return False

        return True

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
    def thumbnail_url(self) -> str:
        """Determine the thumbnail to use for the Discord embed."""
        if self.dice_type != DiceType.D10:
            return "https://em-content.zobj.net/thumbs/240/google/350/game-die_1f3b2.png"
        if self.is_botch:
            return "https://em-content.zobj.net/source/animated-noto-color-emoji/356/face-vomiting_1f92e.gif"
        if self.is_critical:
            return (
                "https://em-content.zobj.net/source/animated-noto-color-emoji/356/rocket_1f680.gif"
            )
        if self.is_success:
            return "https://em-content.zobj.net/thumbs/240/apple/354/thumbs-up_1f44d.png"
        if self.is_failure:
            return "https://em-content.zobj.net/source/animated-noto-color-emoji/356/crying-face_1f622.gif"
        return None

    @property
    def embed_color(self) -> int:
        """Determine the Discord embed color based on the result of the roll."""
        if self.dice_type != DiceType.D10:
            return 0xEA3323
        if self.is_botch:
            return 0xFF2400
        if self.is_critical:
            return 0x37FD12
        if self.is_success:
            return 0x4FC978
        if self.is_failure:
            return 0x808080

        return None

    @property
    def takeaway(self) -> str:
        """The roll's main takeaway--i.e. "SUCCESS", "FAILURE", etc."""
        if self.dice_type != DiceType.D10:
            return "Dice roll"
        if self.is_botch:
            return f"{self.result} SUCCESSES • BOTCH!"
        if self.is_critical:
            return f"{self.result} SUCCESSES • CRITICAL SUCCESS!"
        if self.is_success:
            return f"{self.result} SUCCESSES"
        if self.is_failure:
            return f"{self.result} SUCCESSES"

        return None
