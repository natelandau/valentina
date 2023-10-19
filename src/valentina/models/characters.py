"""Models for working with characters in the database."""
import random
from typing import Literal

import discord
from loguru import logger
from numpy import int32
from numpy.random import default_rng

from valentina.constants import (
    CharClassType,
    CharConcept,
    CharSheetSection,
    HunterCreed,
    RNGCharLevel,
    TraitCategories,
    VampireClanType,
)
from valentina.models.sqlite_models import (
    Character,
    CharacterClass,
    CustomSection,
    GuildUser,
    Trait,
    VampireClan,
)
from valentina.utils import types
from valentina.utils.helpers import (
    adjust_sum_to_match_total,
    divide_into_three,
    fetch_random_name,
    time_now,
)

_rng = default_rng()


class CharacterTraitRandomizer:
    """A class responsible for generating and assigning random trait values to a character.

    This class utilizes a random number generator to simulate trait values for a given
    character based on various factors such as the character's class, level, and concept.
    The generated traits cover attributes, abilities, and disciplines and are influenced
    by predefined distributions and priority settings.

    Attributes:
        character (Character): The character for which traits are to be generated.
        concept (CharConcept): The role or main idea behind the character.
        level (RNGCharLevel): The experience level or proficiency of the character.
        ctx (discord.ApplicationContext): The context related to the discord interaction.
    """

    # TODO: Merits and Flaws
    # TODO: Ghouls
    # TODO: Changelings
    # TODO: Special class

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        concept: CharConcept,
        level: RNGCharLevel,
    ) -> None:
        """Initialize the instance.

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

        # Containers for trait values and custom sections
        self.trait_values: list[tuple[Trait, int]] = []
        self.custom_sections: list[tuple[str, str]] = []

    def _adjust_value_based_on_level(self, value: int) -> int:
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

    def _randomly_assign_backgrounds(self) -> list[tuple[Trait, int]]:
        """Assign backgrounds for the character.

        Returns:
            List[Tuple[Trait, int]]: A list of tuples containing the Trait and its generated value.
        """
        logger.debug(f"CHARGEN: Generate background values for {self.character}")

        if (
            not TraitCategories.BACKGROUNDS.value["COMMON"]
            and not TraitCategories.BACKGROUNDS.value[self.char_class.name]  # type: ignore [literal-required]
        ):
            return []

        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 0,
            RNGCharLevel.ELITE: 1,
        }

        # Don't add backgrounds if the character has no dots to spend
        if (
            self.char_class.value["chargen_background_dots"] == 0
            and extra_dots_map[self.level] == 0
        ):
            return []

        # Determine the total number of dots for the category
        backgrounds = self.traits_by_category[TraitCategories.BACKGROUNDS.name]
        total_dots = self.char_class.value["chargen_background_dots"] + extra_dots_map[self.level]

        # Generate initial random distribution for the traits in the category
        mean, distribution = self.level.value
        initial_values = [
            max(min(x, 5), 0)
            for x in _rng.normal(mean, distribution, len(backgrounds)).astype(int32)
        ]

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(initial_values, total_dots, max_value=5)

        # Return a list of tuples for the traits and their corresponding values
        trait_values = [(t, values.pop(0)) for t in backgrounds]

        logger.debug(f"CHARGEN: Set backgrounds: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def _randomly_assign_virtues(self) -> list[tuple[Trait, int]]:
        """Assign virtues and compute willpower and humanity for the character.

        Determines the virtues, willpower, and humanity for the character, then generates
        trait values.

        Returns:
            List[Tuple[Trait, int]]: A list of tuples containing the Trait and its generated value.
        """
        logger.debug(f"CHARGEN: Generate virtue values for {self.character}")

        if (
            not TraitCategories.VIRTUES.value["COMMON"]
            and not TraitCategories.VIRTUES.value[self.char_class.name]  # type: ignore [literal-required]
        ):
            return []

        virtues = self.traits_by_category[TraitCategories.VIRTUES.name]
        starting_dots = 7
        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 1,
            RNGCharLevel.ELITE: 2,
        }
        total_dots = starting_dots + extra_dots_map[self.level]

        # Divide total dots for each category into three to produce a value for each attribute
        dots_for_each = divide_into_three(total_dots)

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(dots_for_each, total_dots, max_value=5, min_value=1)

        # Pair traits with their generated values
        trait_values = [(t, values.pop(0)) for t in virtues]

        logger.debug(f"CHARGEN: Set virtues: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def _assign_willpower_humanity(self) -> list[tuple[Trait, int]]:
        """Assign willpower, humanity for the character based on the Virtue values."""
        logger.debug(f"CHARGEN: Generate willpower and humanity for {self.character}")
        trait_values = []

        # Don't assign willpower, humanity if the character has no virtues
        if "Self-Control" in TraitCategories.VIRTUES.value[self.char_class.name]:  # type: ignore [literal-required]
            courage = next(y for x, y in self.trait_values if x.name == "Courage")
            self_control = next(y for x, y in self.trait_values if x.name == "Self-Control")
            conscience = next(y for x, y in self.trait_values if x.name == "Conscience")

            trait_values = [(Trait.get(name="Willpower"), courage + self_control)]

            # Some characters gain humanity
            humanity = Trait.get(name="Humanity")
            if humanity in self.traits_by_category[TraitCategories.OTHER.name]:
                trait_values.extend([(humanity, conscience)])

        logger.debug(
            f"CHARGEN: Set willpower, humanity, and conviction: {[(x.name, y) for x, y in trait_values]}"
        )
        return trait_values

    def _hunter_class(self) -> list[tuple[Trait, int]]:
        """Assign trait values for a Hunter character."""
        if self.char_class != CharClassType.HUNTER:
            return []

        try:
            creed = HunterCreed[self.character.data.get("creed", None)]
        except KeyError:
            creed = HunterCreed.random_member()

        # Set willpower and conviction
        trait_values = [
            (Trait.get(name="Willpower"), 3),  # Hunters always start with 3 willpower
            (Trait.get(name="Conviction"), creed.value["conviction"]),
        ]

        # Assign Edges
        edges = creed.value["edges"]
        starting_dots = 5
        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 1,
            RNGCharLevel.ELITE: 2,
        }
        total_dots = starting_dots + extra_dots_map[self.level]

        # Generate initial random distribution for the traits in the category
        mean, distribution = self.level.value
        initial_values = [
            max(min(x, 3), 0) for x in _rng.normal(mean, distribution, len(edges)).astype(int32)
        ]

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(values=initial_values, total=total_dots, max_value=3)

        # Create a list of tuples for the traits and their corresponding values
        trait_values.extend([(Trait.get(name=e), values.pop(0)) for e in edges])

        logger.debug(f"CHARGEN: Set hunter edges: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def _randomly_assign_abilities(
        self, categories: list[TraitCategories]
    ) -> list[tuple[Trait, int]]:
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
        logger.debug(f"CHARGEN: Generate ability values for {self.character}")

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

    def _randomly_assign_attributes(
        self, categories: list[TraitCategories]
    ) -> list[tuple[Trait, int]]:
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
        logger.debug(f"CHARGEN: Generate attribute values for {self.character}")

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

    def _randomly_assign_disciplines(self) -> list[tuple[Trait, int]]:
        """Set discipline trait values for the character based on their clan and level.

        Determines the disciplines relevant to the character's clan and level, then generates
        trait values for each discipline from a normal distribution.

        Returns:
            List[Tuple[Trait, int]]: A list of tuples containing the Trait and its generated value.
        """
        logger.debug(f"CHARGEN: Generate discipline values for {self.character}")

        # Guard clause: Return an empty list if the character doesn't have a clan
        # TODO: Work with Ghouls which have no clan
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
            self._adjust_value_based_on_level(x)
            for x in _rng.normal(mean, distribution, len(disciplines_to_set)).astype(int32)
        ]

        # Pair disciplines with their generated values
        trait_values: list[tuple[Trait, int]] = [(t, values.pop(0)) for t in disciplines_to_set]

        logger.debug(f"CHARGEN: Set attributes: {[(x.name, y) for x, y in trait_values]}")
        return trait_values

    def _concept_special_abilities(self) -> tuple[list[tuple[Trait, int]], list[tuple[str, str]]]:
        """Generate and assign special abilities for the character based on their concept."""
        logger.debug(f"CHARGEN: Generate special ability values for {self.character}")

        # Only mortals and hunters have special abilities
        if self.char_class != CharClassType.MORTAL:
            return [], []

        # Fetch the special abilities
        trait_values: list[tuple[Trait, int]] = []
        custom_sections: list[tuple[str, str]] = []
        for x in self.concept.value["abilities"]:
            if isinstance(x["traits"], list):
                for t in x["traits"]:
                    trait = Trait.get_or_none(name=t[0])
                    if trait:
                        trait_values.append((trait, int(t[1])))

            if isinstance(x["custom_sections"], list):
                custom_sections.extend([(x[0], str(x[1])) for x in x["custom_sections"]])

        logger.debug(f"CHARGEN: Set special abilities: {[(x.name, y) for x, y in trait_values]}")
        return trait_values, custom_sections

    def generate_character(self) -> Character:
        """Set the character's trait values based on the generated trait values.

        Returns:
            Character: The updated character object.
        """
        # Extend trait_values with generated ability values
        self.trait_values.extend(
            self._randomly_assign_abilities(
                categories=[
                    tc
                    for tc in TraitCategories
                    if tc.value["section"] == CharSheetSection.ABILITIES
                ]
            )
        )

        # Extend trait_values with generated attribute values
        self.trait_values.extend(
            self._randomly_assign_attributes(
                categories=[
                    tc
                    for tc in TraitCategories
                    if tc.value["section"] == CharSheetSection.ATTRIBUTES
                ]
            )
        )

        # If Disciplines exist in traits_by_category, extend trait_values with generated discipline values
        if "Disciplines" in self.traits_by_category:
            self.trait_values.extend(self._randomly_assign_disciplines())

        self.trait_values.extend(self._randomly_assign_virtues())
        self.trait_values.extend(self._randomly_assign_backgrounds())

        # Grab special abilities from the character's concept
        traits, sections = self._concept_special_abilities()
        self.trait_values.extend(traits)
        self.custom_sections.extend(sections)

        # Extend trait_values with generated willpower, humanity, and conviction values
        self.trait_values.extend(self._assign_willpower_humanity())

        # Class specific trait values
        self.trait_values.extend(self._hunter_class())

        # Update the character
        for trait, value in self.trait_values:
            self.character.set_trait_value(trait, value)

        for title, description in self.custom_sections:
            self.ctx.bot.char_svc.custom_section_update_or_add(  # type: ignore [attr-defined]
                self.ctx, self.character, title, description
            )

        return Character.get_by_id(self.character.id)


class CharacterService:
    """A service for managing the Player characters in the database."""

    @staticmethod
    def custom_section_update_or_add(
        ctx: discord.ApplicationContext,
        character: Character,
        section_title: str | None = None,
        section_description: str | None = None,
        section_id: int | None = None,
    ) -> CustomSection:
        """Update or add a custom section to a character.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character): The character object to which the custom section will be added.
            section_title (str | None): The title of the custom section. Defaults to None.
            section_description (str | None): The description of the custom section. Defaults to None.
            section_id (int | None): The id of an existing custom section. Defaults to None.

        Returns:
            CustomSection: The updated or created custom section.
        """
        ctx.bot.user_svc.purge_cache(ctx)  # type: ignore [attr-defined]

        if not section_id:
            logger.debug(f"DATABASE: Add custom section to {character}")
            section = CustomSection.create(
                title=section_title,
                description=section_description,
                character=character,
            )

        if section_id:
            section = CustomSection.get_by_id(section_id)
            section.title = section_title
            section.description = section_description
            section.save()

            logger.debug(f"DATABASE: Update custom section for {character}")

        return section

    @staticmethod
    def set_character_default_values() -> None:
        """Set default values for all characters in the database."""
        logger.info("DATABASE: Set default values for all characters")
        characters = Character.select()
        for character in characters:
            character.set_default_data_values()

    @staticmethod
    def fetch_all_player_characters(
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
        owned_by: GuildUser | None = None,
    ) -> list[Character]:
        """Fetch all characters for a specific guild and confirm that default data values are set before returning them as a list.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext): Context object containing guild information.
            owned_by (discord.Member | None, optional): Limit response to a single member who owns the characters. Defaults to None.

        Returns:
            list[Character]: List of characters for the guild.
        """
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        if owned_by:
            characters = Character.select().where(
                Character.guild_id == guild_id,
                Character.data["player_character"] == True,  # noqa: E712
                Character.owned_by == owned_by.id,
            )
        else:
            characters = Character.select().where(
                Character.guild_id == guild_id,
                Character.data["player_character"] == True,  # noqa: E712
            )
        logger.debug(f"DATABASE: Fetch {len(characters)} characters for guild `{guild_id}`")

        # Verify default data values are set
        to_return = []
        for c in characters:
            character = c.set_default_data_values()
            to_return.append(character)

        return to_return

    @staticmethod
    def fetch_all_storyteller_characters(
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
    ) -> list[Character]:
        """Fetch all StoryTeller characters for a guild.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext, optional): Context object containing guild information.

        Returns:
            list[Character]: List of StoryTeller characters for the guild.
        """
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        characters = Character.select().where(
            Character.guild_id == guild_id,
            Character.data["storyteller_character"] == True,  # noqa: E712
        )
        logger.debug(
            f"DATABASE: Fetch {len(characters)} storyteller characters for guild `{guild_id}`"
        )

        # Verify default data values are set
        to_return = []
        for c in characters:
            character = c.set_default_data_values()
            to_return.append(character)

        return to_return

    @staticmethod
    async def update_or_add(
        ctx: discord.ApplicationContext,
        data: dict[str, str | int | bool] | None = None,
        character: Character | None = None,
        char_class: CharClassType | None = CharClassType.NONE,
        clan: VampireClanType | None = None,
        **kwargs: str | int,
    ) -> Character:
        """Update or add a character.

        Args:
            ctx (ApplicationContext): The application context.
            data (dict[str, str | int | bool] | None): The character data.
            character (Character | None): The character to update, or None to create.
            char_class (CharClassType | None): The character class.
            clan (VampireClanType | None): The vampire clan.
            **kwargs: Additional fields for the character.

        Returns:
            Character: The updated or created character.
        """
        # Purge the user's character cache
        ctx.bot.user_svc.purge_cache(ctx)  # type: ignore [attr-defined]

        # Always add the modified timestamp if data is provided.
        if data:
            data["modified"] = str(time_now())

        if not character:
            user = await ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

            new_character = Character.create(
                guild_id=ctx.guild.id,
                created_by=user,
                owned_by=user,
                char_class=CharacterClass.get_or_none(name=char_class.name),
                clan=VampireClan.get_or_none(name=clan.name) if clan else None,
                data=data or {},
                **kwargs,
            )
            character = new_character.set_default_data_values()

            logger.info(f"DATABASE: Create {character} for {ctx.author.display_name}")

            return character

        if data:
            Character.update(data=Character.data.update(data)).where(
                Character.id == character.id
            ).execute()

        if kwargs:
            Character.update(**kwargs).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Updated Character '{character}'")

        return Character.get_by_id(character.id)  # Have to query db again to get updated data ???

    async def rng_creator(
        self,
        ctx: discord.ApplicationContext,
        char_class: CharClassType | None = None,
        concept: CharConcept | None = None,
        vampire_clan: VampireClanType | None = None,
        character_level: RNGCharLevel | None = None,
        player_character: bool = False,
        storyteller_character: bool = False,
        developer_character: bool = False,
        chargen_character: bool = False,
        gender: Literal["male", "female"] | None = None,
        nationality: str = "us",
        nickname_is_class: bool = False,
    ) -> Character:
        """Create a random character."""
        # Add a random name

        name = await fetch_random_name(gender=gender, country=nationality)
        first_name, last_name = name[0]

        data: dict[str, str | int | bool] = {
            "first_name": first_name,
            "last_name": last_name,
        }

        # Add character metadata
        if char_class is None:
            percentile = _rng.integers(1, 101)
            char_class = CharClassType.get_member_by_value(percentile)

        if nickname_is_class:
            data["nickname"] = char_class.value["name"]

        if concept is None:
            percentile = _rng.integers(1, 101)
            concept = CharConcept.get_member_by_value(percentile)
        data["concept_readable"] = concept.value["name"]
        data["concept_db"] = concept.name

        if character_level is None:
            character_level = RNGCharLevel.random_member()
        data["rng_level"] = character_level.name.title()

        if char_class == CharClassType.VAMPIRE and not vampire_clan:
            vampire_clan = VampireClanType.random_member()

        if char_class == CharClassType.HUNTER:
            percentile = _rng.integers(1, 101)
            creed = HunterCreed.get_member_by_value(percentile)
            data["creed"] = creed.name

        data["player_character"] = player_character
        data["storyteller_character"] = storyteller_character
        data["developer_character"] = developer_character
        data["chargen_character"] = chargen_character

        # Add character to database
        character = await self.update_or_add(
            ctx,
            char_class=CharacterClass.get(name=char_class.name),
            clan=VampireClan(name=vampire_clan.name) if vampire_clan else None,
            data=data,
        )

        randomizer = CharacterTraitRandomizer(
            ctx=ctx, character=character, concept=concept, level=character_level
        )
        character = randomizer.generate_character()
        # TODO: Add specialties, backgrounds, etc.
        logger.debug(f"CHARGEN: Created {character} from RNG")
        return character
