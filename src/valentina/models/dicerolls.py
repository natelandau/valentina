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
    from valentina.discord.bot import ValentinaContext


class DiceRoll:
    """Represent a dice roll and its results.

    This class encapsulates the logic for performing a dice roll, including
    handling different pool sizes, difficulties, and dice types. It also
    manages the recording of roll statistics and provides methods for
    interpreting and presenting roll results.

    Use this class to:
    - Create and execute dice rolls with various parameters
    - Calculate and interpret roll results
    - Log roll statistics for characters, campaigns, and guilds
    - Generate formatted output for displaying roll results

    Attributes:
        ctx (Optional[ValentinaContext]): The context of the command, if available
        character (Optional[Character]): The character associated with the roll
        desperation_pool (int): Number of dice in the desperation pool
        campaign (Optional[Campaign]): The campaign associated with the roll
        guild_id (Optional[int]): The ID of the guild where the roll was made
        author_id (Optional[int]): The ID of the user who made the roll
        author_name (Optional[str]): The name of the user who made the roll
        dice_type (DiceType): The type of dice used for the roll
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
        """A container class that determines the result of a roll."""
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
        """Calculate and return the result type of the roll.

        Determine the outcome of the dice roll based on the dice type, result value,
        and pool size. Use the following criteria:

        - For non-d10 dice: Always return RollResultType.OTHER.
        - For d10 dice:
          - If result < 0: Return RollResultType.BOTCH.
          - If result == 0: Return RollResultType.FAILURE.
          - If result > pool: Return RollResultType.CRITICAL.
          - Otherwise: Return RollResultType.SUCCESS.

        Returns:
            RollResultType: The calculated result type of the roll.
        """
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
        """Log the roll to the database for statistical analysis.

        Record the details of the current dice roll in the database, including
        information about the roll result, character, and associated traits.
        This method is crucial for maintaining historical data and generating
        roll statistics.

        Args:
            traits (list[str], optional): A list of trait names associated with
                the roll. Use this to track which character traits were involved
                in the roll. Defaults to an empty list.

        Note:
            This method only logs d10 rolls to the database. Other dice types
            are not recorded for statistical purposes.
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
        """Determine and return the result type of the roll.

        Calculate the result type based on the roll outcome if not already determined.
        The result type is cached to avoid recalculation on subsequent accesses.

        Returns:
            RollResultType: An enum representing the outcome of the roll
                (e.g., BOTCH, FAILURE, SUCCESS, CRITICAL).

        Note:
            This property uses lazy evaluation, calculating the result type
            only when first accessed and storing it for future use.
        """
        if not self._result_type:
            self._result_type = self._calculate_result()  # type: ignore [unreachable]

        return self._result_type

    @property
    def roll(self) -> list[int]:
        """Roll the dice and return the results.

        Generate random numbers for each die in the pool and store them.
        If the roll has not been performed yet, execute it and cache the results.
        Return the list of rolled values.

        Returns:
            list[int]: A list of integers representing the results of the dice roll.

        Note:
            This property uses lazy evaluation, performing the roll only when
            first accessed and storing the results for future use.
        """
        if not self._roll:
            self._roll = [int(random_num(self.dice_type.value)) for x in range(self.pool)]

        return self._roll

    @property
    def desperation_roll(self) -> list[int]:
        """Roll the desperation dice and return the results.

        Generate random numbers for each die in the desperation pool and store them.
        If the desperation roll has not been performed yet, execute it and cache the results.
        Return the list of rolled values for the desperation dice.

        Returns:
            list[int]: A list of integers representing the results of the desperation dice roll.

        Note:
            This property uses lazy evaluation, performing the roll only when
            first accessed and storing the results for future use.
        """
        if not self._desperation_roll:
            self._desperation_roll = [
                random_num(self.dice_type.value) for x in range(self.desperation_pool)
            ]

        return self._desperation_roll

    @property
    def botches(self) -> int:
        """Calculate and return the number of botches (ones) in the dice roll.

        Count the number of dice that rolled a 1, which are considered botches.
        Include both regular and desperation dice in the count if applicable.
        Use lazy evaluation to calculate the result only when first accessed.

        Returns:
            int: The total number of botches (ones) in the dice roll.
        """
        if not self._botches:
            if self.desperation_pool > 0:
                desperation_botches = self.desperation_roll.count(1)
                self._botches = self.roll.count(1) + desperation_botches
            else:
                self._botches = self.roll.count(1)

        return self._botches

    @property
    def desperation_botches(self) -> int:
        """Calculate and return the number of botches in the desperation dice roll.

        Count the number of ones (botches) rolled on the desperation dice.
        Use lazy evaluation to calculate the result only when first accessed.
        Cache the result for subsequent accesses to improve performance.

        Returns:
            int: The number of ones (botches) in the desperation dice roll.

        Note:
            This property returns 0 if there is no desperation pool.
        """
        if not self._desperation_botches and self.desperation_pool > 0:
            self._desperation_botches = self.desperation_roll.count(1)

        return self._desperation_botches

    @property
    def criticals(self) -> int:
        """Calculate and return the number of critical successes in the dice roll.

        Count the number of dice that rolled the highest possible value for the
        given dice type, which are considered critical successes. Include both
        regular and desperation dice in the count if applicable. Use lazy
        evaluation to calculate the result only when first accessed.

        Returns:
            int: The total number of critical successes in the dice roll.
        """
        if not self._criticals:
            if self.desperation_pool > 0:
                desperation_criticals = self.desperation_roll.count(self.dice_type.value)
                self._criticals = self.roll.count(self.dice_type.value) + desperation_criticals
            else:
                self._criticals = self.roll.count(self.dice_type.value)

        return self._criticals

    @property
    def failures(self) -> int:
        """Calculate and return the number of failed dice rolls, excluding botches.

        Count the dice rolls that are above 1 (not botches) but below the difficulty threshold.
        This property represents unsuccessful attempts that are not critical failures.

        Returns:
            int: The number of failed dice rolls, not including botches.

        Note:
            This property uses lazy evaluation and caches the result for subsequent accesses.
            It includes both regular and desperation dice rolls if applicable.
        """
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
        """Calculate and return the total number of successful dice rolls, excluding criticals.

        Count the dice rolls that meet or exceed the difficulty threshold but are not
        critical successes. Include both regular and desperation dice if applicable.

        Returns:
            int: The number of successful dice rolls, not including criticals.

        Note:
            Use lazy evaluation to calculate the result only when first accessed.
            Cache the result for subsequent accesses to improve performance.
        """
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
        """Calculate and return the final result of the dice roll.

        Determine the total number of successes to count, considering criticals,
        failures, and botches. For d10 rolls, apply special rules for criticals
        and botches. Use lazy evaluation to calculate the result only when first
        accessed and cache it for subsequent accesses.

        Returns:
            int: The final result of the dice roll, representing the total
                 number of successes to count.
        """
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
        """Determine and return the thumbnail URL for the Discord embed.

        Fetch the appropriate thumbnail URL based on the roll result type from the
        Guild's custom roll result thumbnails. If no custom thumbnail is set, use
        the default thumbnail for the given result type.

        Returns:
            str: The URL of the thumbnail image to be used in the Discord embed.
        """
        guild = await Guild.get(self.guild_id or self.ctx.guild.id)
        return await guild.fetch_diceroll_thumbnail(self.result_type)

    @property
    def embed_color(self) -> int:  # pragma: no cover
        """Determine the Discord embed color based on the result of the roll.

        Return an integer color value corresponding to the roll result type.
        Use predefined color mappings for different roll outcomes:
        - OTHER: Info color
        - BOTCH: Error color
        - CRITICAL: Success color
        - SUCCESS: Success color
        - FAILURE: Warning color

        Returns:
            int: The color value to be used in the Discord embed.
        """
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
        """Return a human-readable description of the dice roll result.

        Generate a concise, user-friendly string that describes the outcome of the dice roll.
        The description varies based on the roll's result type, providing context-appropriate
        feedback such as "Botch!", "Critical Success!", or a specific number of successes.

        Returns:
            str: A human-readable string describing the roll result, e.g., "Botch!", "2 successes", etc.
        """
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
        """Return the number of successes as a humanized string.

        Generate a string representation of the number of successes rolled,
        formatted as 'x successes'. Use proper pluralization for 'success'
        based on the number of successes.

        Returns:
            str: A human-readable string describing the number of successes,
                 e.g., '1 success', '2 successes', etc.
        """
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
        """Convert the rolled dice values to emoji images and return as a string.

        Generate a string representation of the dice roll results using emoji images.
        Sort the dice values in ascending order before conversion. Use the
        convert_int_to_emoji function to transform each die value into its
        corresponding emoji image.

        Returns:
            str: A space-separated string of emoji images representing the rolled dice.

        Note:
            This property uses lazy evaluation, generating the emoji string only
            when first accessed and caching it for future use.
        """
        if not self._dice_as_emoji_images:
            self._dice_as_emoji_images = " ".join(
                f"{convert_int_to_emoji(die, images=True)}" for die in sorted(self.roll)
            )
        return self._dice_as_emoji_images

    @property
    def desperation_dice_as_emoji_images(self) -> str:
        """Convert the rolled desperation dice values to emoji images and return as a string.

        Generate a string representation of the desperation dice roll results using emoji images.
        Sort the dice values in ascending order before conversion. Use the
        convert_int_to_emoji function to transform each die value into its
        corresponding emoji image.

        Returns:
            str: A space-separated string of emoji images representing the rolled desperation dice.

        Note:
            This property uses lazy evaluation, generating the emoji string only
            when first accessed and caching it for future use.
        """
        if not self._desperation_dice_as_emoji_images:
            self._desperation_dice_as_emoji_images = " ".join(
                f"{convert_int_to_emoji(die, images=True)}" for die in sorted(self.desperation_roll)
            )
        return self._desperation_dice_as_emoji_images
