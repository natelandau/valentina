"""Helper utilities for building storyteller characters."""
import random

import discord
from loguru import logger
from numpy import int32
from numpy.random import default_rng

from valentina.constants import (
    CharClassType,
    CharConcept,
    RNGCharLevel,
    TraitCategories,
    VampireClanType,
)
from valentina.models.db_tables import Character, Trait
from valentina.utils import types
from valentina.utils.helpers import (
    adjust_sum_to_match_total,
    divide_into_three,
)

_rng = default_rng()


class RNGTraitValues:
    """Generate random trait values using a random number generator."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        concept: CharConcept,
        level: RNGCharLevel,
    ) -> None:
        """Initialize the RNGTraitValues instance.

        Populate the instance with traits and trait categories based on the given character, concept, and level.

        Args:
            ctx (discord.ApplicationContext): The context of the slash command.
            character (Character): The character for which to generate trait values.
            concept (CharConcept): The concept of the character.
            level (RNGCharLevel): The level of the character.
        """
        self.character = character
        self.concept = concept
        self.level = level
        self.ctx = ctx
        self.mean, self.distribution = self.level.value

        # Fetch character class and clan types
        self.char_class = CharClassType[character.char_class.name]
        self.clan = VampireClanType[character.clan.name] if character.clan else None

        # Safely fetch all traits for the character class
        self.traits = self.ctx.bot.trait_svc.fetch_all_class_traits(self.char_class)  # type: ignore [attr-defined]

        # Categorize traits for easier processing
        self.traits_by_category: dict[str, list[Trait]] = {
            category: [trait for trait in self.traits if trait.category.name == category]
            for category in {trait.category.name for trait in self.traits}
        }
        logger.debug(f"CHARGEN: Initialized RNGTraitValues for {self.character}")

    def _set_attributes(self, categories: list[TraitCategories]) -> list[tuple[Trait, int]]:
        """Generate and assign attribute trait values for the character.

        Filter the available traits based on the provided attribute categories. Then, calculate the total number of dots (trait values)
        to be distributed across these attributes. The distribution is influenced by the character's class, level, and concept.

        The function first determines the starting dot distribution based on the character's class. It then adds extra dots based on the character's level.
        The total dots are then divided among primary, secondary, and tertiary categories, which are determined based on the character's concept.

        Finally, the function generates a list of tuples, each containing a trait and its corresponding value (number of dots).

        Args:
            categories (list[str]): List of attribute categories to consider.


        Returns:
            list[tuple[Trait, int]]: A list of tuples, where each tuple contains a Trait object and an integer representing the number of dots assigned to that trait.
        """
        # Filter traits by attribute categories
        attributes: dict[str, list[Trait]] = {
            cat: traits
            for cat, traits in self.traits_by_category.items()
            if TraitCategories[cat] in categories
        }

        # Initialize dot distribution based on character level and class. Each is three dot higher than a player would select b/c each attribute starts with one dot before a user applies their selection
        starting_dot_distribution = (
            [9, 8, 6]
            if self.char_class in (CharClassType.MORTAL, CharClassType.HUNTER)
            else [10, 8, 6]
        )
        extra_dots_map = {
            RNGCharLevel.NEW: [0, 0, 0],
            RNGCharLevel.INTERMEDIATE: [1, 0, 0],
            RNGCharLevel.ADVANCED: [2, 1, 0],
            RNGCharLevel.ELITE: [3, 2, 1],
        }
        total_dots = [
            a + b
            for a, b in zip(starting_dot_distribution, extra_dots_map[self.level], strict=True)
        ]

        # Determine category priority based on the character's concept
        primary_category = self.concept.value["attribute_specialty"]
        categories.remove(primary_category)
        secondary_category = random.choice(categories)
        categories.remove(secondary_category)
        tertiary_category = random.choice(categories)

        category_priority: list[types.CharGenCategoryDict] = [
            {"total_dots": total_dots.pop(0), "category": cat.name}
            for cat in [primary_category, secondary_category, tertiary_category]
        ]

        # Initialize container for trait values
        trait_values: list[tuple[Trait, int]] = []

        # Set the attribute values based on category priority
        for priority in category_priority:
            cat = priority["category"]
            priority_dots = priority["total_dots"]

            # Divide total dots for each category into three to produce a value for each attribute
            dots_for_each = divide_into_three(priority_dots)

            # Adjust the sum of the list to match the total dots for the category
            values = adjust_sum_to_match_total(
                dots_for_each, priority_dots, max_value=5, min_value=1
            )

            # Pair traits with their generated values
            trait_values.extend([(t, values.pop(0)) for t in attributes[cat]])

        logger.debug(f"CHARGEN: Set attributes: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def __adjust_discipline_value(self, value: int) -> int:
        """Adjust the discipline value based on the character's level.

        For advanced and elite levels, the value is incremented by 1.
        For new characters, the value is capped at 3.
        The final value is constrained between 1 and 5.

        Args:
            value (int): The initial discipline value.

        Returns:
            int: The adjusted discipline value.
        """
        # Increment value for advanced and elite levels
        if self.level in {RNGCharLevel.ADVANCED, RNGCharLevel.ELITE}:
            value += 1

        # Cap values based on character level
        if self.level == RNGCharLevel.NEW and value > 2:  # noqa: PLR2004
            value = 2

        if self.level == RNGCharLevel.INTERMEDIATE and value > 3:  # noqa: PLR2004
            value = 3

        # Constrain the final value between 1 and 5
        return max(min(value, 5), 1)

    def _set_disciplines(self) -> list[tuple[Trait, int]]:
        """Set discipline trait values for the character based on their clan and level.

        Determines the disciplines relevant to the character's clan and level, then generates
        trait values for each discipline from a normal distribution.

        Returns:
            List[Tuple[Trait, int]]: A list of tuples containing the Trait and its generated value.
        """
        # Guard clause: Return an empty list if the character doesn't have a clan
        if not self.character.clan:
            return []

        # Fetch all disciplines and map extra disciplines based on character level
        all_disciplines = self.traits_by_category[TraitCategories.DISCIPLINES.name]
        extra_disciplines_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 1,
            RNGCharLevel.ADVANCED: 2,
            RNGCharLevel.ELITE: 3,
        }

        # Determine disciplines relevant to the character's clan
        clan_disciplines = VampireClanType[self.character.clan.name].value["disciplines"]
        disciplines_to_set = [x for x in all_disciplines if x.name in clan_disciplines]

        # Add extra disciplines based on character level
        extra_disciplines = [x for x in all_disciplines if x.name not in clan_disciplines]
        disciplines_to_set.extend(
            random.sample(extra_disciplines, extra_disciplines_map.get(self.level, 0))
        )

        # Generate trait values from a normal distribution
        mean, distribution = self.level.value
        values = [
            self.__adjust_discipline_value(x)
            for x in _rng.normal(mean, distribution, len(disciplines_to_set)).astype(int32)
        ]

        # Pair disciplines with their generated values
        trait_values: list[tuple[Trait, int]] = [(t, values.pop(0)) for t in disciplines_to_set]

        logger.debug(f"CHARGEN: Set attributes: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def _set_abilities(self, categories: list[TraitCategories]) -> list[tuple[Trait, int]]:
        """Assign ability values to the character based on specified categories and character level.

        Initialize the character's abilities by filtering out relevant traits based on the given categories.
        Calculate the total number of 'dots' or points that can be allocated to each category based on the character's level.

        The function performs the following steps:
        1. Filters traits that belong to the specified categories.
        2. Determines the total number of dots available for each category based on the character's level.
        3. Prioritizes the categories based on the character's concept and randomly for remaining categories.
        4. Distributes the dots across the abilities in each category, ensuring the sum matches the total dots for that category.
        5. Optionally swaps zero values with higher values based on the character's specific abilities.

        Args:
            categories (list[str]): A list of ability categories to consider for the character.

        Returns:
            list[tuple[Trait, int]]: A list of tuples, each containing a Trait object and its corresponding value.
        """
        # Filter traits by attribute categories
        filtered_traits: dict[str, list[Trait]] = {
            cat: traits
            for cat, traits in self.traits_by_category.items()
            if TraitCategories[cat] in categories
        }

        # Initialize dot distribution based on character level
        starting_dot_distribution = [13, 9, 5]
        extra_dots_map = {
            RNGCharLevel.NEW: [0, 0, 0],
            RNGCharLevel.INTERMEDIATE: [5, 3, 1],
            RNGCharLevel.ADVANCED: [10, 6, 3],
            RNGCharLevel.ELITE: [15, 9, 5],
        }
        total_dots = [
            a + b
            for a, b in zip(starting_dot_distribution, extra_dots_map[self.level], strict=True)
        ]

        # Initialize category priority
        primary_category = self.concept.value["ability_specialty"]
        categories.remove(primary_category)
        secondary_category = random.choice(categories)
        categories.remove(secondary_category)
        tertiary_category = random.choice(categories)

        category_priority: list[types.CharGenCategoryDict] = [
            {"total_dots": total_dots.pop(0), "category": cat.name}
            for cat in [primary_category, secondary_category, tertiary_category]
        ]

        # Initialize the list to store the final trait values
        trait_values: list[tuple[Trait, int]] = []

        # Set the ability values
        for priority in category_priority:
            cat = priority["category"]
            category_dots = priority["total_dots"]
            category_traits = list(filtered_traits[cat])

            # Generate initial random distribution for the traits in the category
            mean, distribution = self.level.value
            initial_values = [
                max(min(x, 5), 0)
                for x in _rng.normal(mean, distribution, len(category_traits)).astype(int32)
            ]

            # Adjust the sum of the list to match the total dots for the category
            values = adjust_sum_to_match_total(initial_values, category_dots, max_value=5)

            # Create a list of tuples for the traits and their corresponding values
            category_trait_values: list[tuple[Trait, int]] = [
                (t, values.pop(0)) for t in category_traits
            ]

            # Perform any necessary value swaps based on the concept's specific abilities
            specified_abilities = self.concept.value["specific_abilities"]
            for name in specified_abilities:
                # Find a tuple where Trait.name matches and the integer is zero
                zero_value_tuple = next(
                    (t for t in category_trait_values if t[0].name == name and t[1] == 0), None
                )

                if zero_value_tuple:
                    # Find a tuple with the highest integer where Trait.name does not match any string in names_to_match
                    highest_value_tuple = max(
                        (t for t in category_trait_values if t[0].name not in specified_abilities),
                        key=lambda x: x[1],
                        default=None,
                    )

                    if highest_value_tuple:
                        # Swap the integers
                        zero_value_tuple_index = category_trait_values.index(zero_value_tuple)
                        highest_value_tuple_index = category_trait_values.index(highest_value_tuple)

                        category_trait_values[zero_value_tuple_index] = (
                            zero_value_tuple[0],
                            highest_value_tuple[1],
                        )
                        category_trait_values[highest_value_tuple_index] = (
                            highest_value_tuple[0],
                            zero_value_tuple[1],
                        )

            # Add the trait values to the list of trait values
            trait_values.extend(category_trait_values)

        logger.debug(f"CHARGEN: Set abilities: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def generate_trait_values(self) -> list[tuple[Trait, int]]:
        """Update the character's traits based on randomly generated values.

        This method calls other methods to set attribute, ability, and discipline values for the character.
        The generated trait values are then stored in the `trait_values` attribute of the instance.

        Returns:
            List[Tuple[Trait, int]]: A list of tuples, where each tuple contains a Trait object and an integer representing the number of dots assigned to that trait.

        """
        # Initialize or clear the trait_values list
        trait_values: list[tuple[Trait, int]] = []

        # Extend trait_values with generated attribute values
        logger.debug(f"CHARGEN: Generate attribute values for {self.character}")
        trait_values.extend(
            self._set_attributes(
                categories=[
                    TraitCategories.PHYSICAL,
                    TraitCategories.SOCIAL,
                    TraitCategories.MENTAL,
                ]
            )
        )

        # Extend trait_values with generated ability values
        logger.debug(f"CHARGEN: Generate ability values for {self.character}")
        trait_values.extend(
            self._set_abilities(
                categories=[
                    TraitCategories.TALENTS,
                    TraitCategories.SKILLS,
                    TraitCategories.KNOWLEDGES,
                ]
            )
        )

        # If Disciplines exist in traits_by_category, extend trait_values with generated discipline values
        if "Disciplines" in self.traits_by_category:
            logger.debug(f"CHARGEN: Generate discipline values for {self.character}")
            trait_values.extend(self._set_disciplines())

        return trait_values

    def set_trait_values(self) -> Character:
        """Set the character's trait values based on the generated trait values.

        This method iterates through the trait_values attribute and sets the value of each trait to the corresponding value in the list.

        Returns:
            Character: The updated character object.
        """
        for trait, value in self.generate_trait_values():
            self.character.set_trait_value(trait, value)

        return self.character
