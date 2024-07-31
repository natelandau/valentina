"""Models for dice rolls."""

from typing import TYPE_CHECKING, Optional

import inflect
from loguru import logger

from valentina.constants import MAX_POOL_SIZE, DiceType, EmbedColor, RollResultType
from valentina.models import Campaign, Character, Guild, RollStatistic
from valentina.utils import errors, random_num
from valentina.utils.helpers import convert_int_to_emoji

p = inflect.engine()

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


class DiceRoll:
    """A container class that determines the result of a roll and logs dicerolls to the database.

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
        desperation_roll (list[int]): A list of the result all rolled desperation dice.
        desperation_botches (int): The number of ones in the desperation dice.
        dice_type (DiceType): The type of dice to roll.
        difficulty (int): The difficulty of the roll.
        embed_color (int): The color of the embed.
        failures (int): The number of unsuccessful dice not including botches.
        is_botch (bool): Whether the roll is a botch.
        is_critical (bool): Whether the roll is a critical success.
        is_failure (bool): Whether the roll is a failure.
        is_success (bool): Whether the roll is a success.
        roll_result_humanized (str): The result of the roll, humanized
        num_successes_humanized (str): The number of successes, humanized
        pool (int): The pool's total size, including hunger.
        result (int): The number of successes after accounting for botches and cancelling ones and tens.
        result_type(RollResultType): The result type of the roll.
        roll (list[int]): A list of the result all rolled dice.
        successes (int): The number of successful dice not including criticals.
    """

    def __init__(
        self,
        pool: int,
        ctx: Optional["ValentinaContext"] = None,
        difficulty: int = 6,
        dice_size: int = 10,
        character: Character = None,
        desperation_pool: int = 0,
        campaign: Campaign = None,
        guild_id: int | None = None,
        author_id: int | None = None,
        author_name: str | None = None,
    ) -> None:
        """A container class that determines the result of a roll.

        Args:
            author_id (int, optional): The author ID to log the roll for. Defaults to None.
            author_name (str, optional): The author name to log the roll for. Defaults to None.
            campaign (Campaign, optional): The campaign to log the roll for. Defaults to None.
            character (Character, optional): The character to log the roll for. Defaults to None.
            ctx (ValentinaContext, optional): The context of the command.
            desperation_pool (int): The number of dice to roll from the desperation pool. Defaults to 0.
            dice_size (int, optional): The size of the dice. Defaults to 10.
            difficulty (int, optional): The difficulty of the roll. Defaults to 6.
            guild_id (int, optional): The guild ID to log the roll for. Defaults to None.
            pool (int): The pool's total size, including hunger
        """
        self.ctx = ctx
        self.character = character
        self.desperation_pool = desperation_pool
        self.campaign = campaign
        self.guild_id = guild_id
        self.author_id = author_id
        self.author_name = author_name

        if not self.ctx and (not self.guild_id or not self.author_id or not self.author_name):
            msg = "A context must be provided if guild_id, author_id, or author_name are not provided."
            raise errors.ValidationError(msg)

        dice_size_values = [member.value for member in DiceType]
        if dice_size not in dice_size_values:
            msg = f"Invalid dice size `{dice_size}`."
            raise errors.ValidationError(msg)

        self.dice_type = DiceType(dice_size)

        if difficulty < 0:
            msg = f"Difficulty cannot be less than 0. (Got `{difficulty}`.)"
            raise errors.ValidationError(msg)
        if difficulty > self.dice_type.value:
            msg = f"Difficulty cannot exceed the size of the dice. (Got `{difficulty}` for `{self.dice_type.name}`.)"
            raise errors.ValidationError(msg)
        if pool < 0:
            msg = f"Pool cannot be less than 0. (Got `{pool}`.)"
            raise errors.ValidationError(msg)
        if pool > MAX_POOL_SIZE:
            msg = f"Pool cannot exceed {MAX_POOL_SIZE}. (Got `{pool}`.)"
            raise errors.ValidationError(msg)

        self.difficulty = difficulty
        self.pool = pool

        # Set property defaults
        self._roll: list[int] = None
        self._desperation_roll: list[int] = None
        self._botches: int = None
        self._criticals: int = None
        self._failures: int = None
        self._successes: int = None
        self._result: int = None
        self._result_type: RollResultType = None
        self._desperation_botches: int = None
        self._dice_as_emoji_images: str = None
        self._desperation_dice_as_emoji_images: str = None

    def _calculate_result(self) -> RollResultType:
        """Calculate the result type of the roll."""
        if self.dice_type != DiceType.D10:
            return RollResultType.OTHER

        if self.result < 0:
            return RollResultType.BOTCH

        if self.result == 0:
            return RollResultType.FAILURE

        if self.result > self.pool:
            return RollResultType.CRITICAL

        return RollResultType.SUCCESS

    async def log_roll(self, traits: list[str] = []) -> None:
        """Log the roll to the database.

        Args:
            traits (list[str], optional): The traits to log the roll for. Defaults to [].
        """
        # Ensure the user in the database to avoid foreign key errors

        # Log the roll to the database
        if self.dice_type == DiceType.D10:
            stat = RollStatistic(
                guild=self.guild_id or self.ctx.guild.id,
                user=self.author_id or self.ctx.author.id,
                character=str(self.character.id) if self.character else None,
                result=self.result_type,
                pool=self.pool,
                difficulty=self.difficulty,
                traits=traits,
                campaign=str(self.campaign.id) if self.campaign else None,
            )
            await stat.insert()

            logger.debug(
                f"DICEROLL: {self.author_name or self.ctx.author.display_name} rolled {self.roll} for {self.result_type.name}"
            )

    @property
    def result_type(self) -> RollResultType:
        """Retrieve the result type of the roll."""
        if not self._result_type:
            self._result_type = self._calculate_result()

        return self._result_type

    @property
    def roll(self) -> list[int]:
        """Roll the dice and return the results."""
        if not self._roll:
            self._roll = [random_num(self.dice_type.value) for x in range(self.pool)]

        return self._roll

    @property
    def desperation_roll(self) -> list[int]:
        """Roll the desperation dice and return the results."""
        if not self._desperation_roll:
            self._desperation_roll = [
                random_num(self.dice_type.value) for x in range(self.desperation_pool)
            ]

        return self._desperation_roll

    @property
    def botches(self) -> int:
        """Retrieve the number of ones in the dice."""
        if not self._botches:
            if self.desperation_pool > 0:
                desperation_botches = self.desperation_roll.count(1)
                self._botches = self.roll.count(1) + desperation_botches
            else:
                self._botches = self.roll.count(1)

        return self._botches

    @property
    def desperation_botches(self) -> int:
        """Retrieve the number of ones in the desperation dice."""
        if not self._desperation_botches and self.desperation_pool > 0:
            self._desperation_botches = self.desperation_roll.count(1)

        return self._desperation_botches

    @property
    def criticals(self) -> int:
        """Retrieve the number of rolled criticals (Highest number on dice)."""
        if not self._criticals:
            if self.desperation_pool > 0:
                desperation_criticals = self.desperation_roll.count(self.dice_type.value)
                self._criticals = self.roll.count(self.dice_type.value) + desperation_criticals
            else:
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

        if self.desperation_pool > 0:
            desperation_failures = 0
            for die in self.desperation_roll:
                if 2 <= die <= self.difficulty - 1:  # noqa: PLR2004
                    desperation_failures += 1
            self._failures += desperation_failures

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

        if self.desperation_pool > 0:
            desperation_successes = 0
            for die in self.desperation_roll:
                if self.difficulty <= die <= self.dice_type.value - 1:
                    desperation_successes += 1
            self._successes += desperation_successes

        return self._successes

    @property
    def result(self) -> int:
        """Retrieve the number of successes to count."""
        if not self._result:
            if self.dice_type != DiceType.D10:
                self._result = self.successes + self.criticals - self.failures - self.botches
            else:
                botches = self.botches - self.criticals
                botches = max(0, botches)
                criticals = self.criticals - self.botches
                criticals = max(0, criticals)

                self._result = self.successes + (criticals * 2) - (botches * 2)

        return self._result

    async def thumbnail_url(self) -> str:  # pragma: no cover
        """Determine the thumbnail to use for the Discord embed."""
        guild = await Guild.get(self.guild_id or self.ctx.guild.id)
        return await guild.fetch_diceroll_thumbnail(self.result_type)

    @property
    def embed_color(self) -> int:  # pragma: no cover
        """Determine the Discord embed color based on the result of the roll."""
        color_map = {
            RollResultType.OTHER: EmbedColor.INFO,
            RollResultType.BOTCH: EmbedColor.ERROR,
            RollResultType.CRITICAL: EmbedColor.SUCCESS,
            RollResultType.SUCCESS: EmbedColor.SUCCESS,
            RollResultType.FAILURE: EmbedColor.WARNING,
        }
        return color_map[self.result_type].value

    @property
    def roll_result_humanized(self) -> str:
        """The humanized result of the dice roll. ie - "botch", "2 successes", etc."""
        title_map = {
            RollResultType.OTHER: "Dice roll",
            RollResultType.BOTCH: "Botch!",
            RollResultType.CRITICAL: "Critical Success!",
            RollResultType.SUCCESS: "Success",
            RollResultType.FAILURE: "Failure",
        }
        return title_map[self.result_type]

    @property
    def num_successes_humanized(self) -> str:
        """The number of successes rolled written as `x successess`."""
        description_map = {
            RollResultType.OTHER: "",
            RollResultType.BOTCH: f"{self.result} {p.plural_noun('Success', self.result)}",
            RollResultType.CRITICAL: f"{self.result} {p.plural_noun('Success', self.result)}",
            RollResultType.SUCCESS: f"{self.result} {p.plural_noun('SUCCESS', self.result)}",
            RollResultType.FAILURE: f"{self.result} {p.plural_noun('SUCCESS', self.result)}",
        }
        return description_map[self.result_type]

    @property
    def dice_as_emoji_images(self) -> str:
        """Return the rolled dice as emoji images."""
        if not self._dice_as_emoji_images:
            self._dice_as_emoji_images = " ".join(
                f"{convert_int_to_emoji(die, images=True)}" for die in sorted(self.roll)
            )
        return self._dice_as_emoji_images

    @property
    def desperation_dice_as_emoji_images(self) -> str:
        """Return the rolled desperation dice as emoji images."""
        if not self._desperation_dice_as_emoji_images:
            self._desperation_dice_as_emoji_images = " ".join(
                f"{convert_int_to_emoji(die, images=True)}" for die in sorted(self.desperation_roll)
            )
        return self._desperation_dice_as_emoji_images
