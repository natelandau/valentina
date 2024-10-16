"""Random character generation controller."""

import random
from typing import Literal, cast

from loguru import logger
from numpy import int32
from numpy.random import default_rng

from valentina.constants import (
    CharacterConcept,
    CharClass,
    HunterCreed,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.models import Campaign, Character, CharacterSheetSection, CharacterTrait, User
from valentina.utils import random_num
from valentina.utils.helpers import (
    divide_total_randomly,
    fetch_random_name,
    get_max_trait_value,
)

_rng = default_rng()


class RNGCharGen:
    """Randomly generate different parts of a character.

    This class provides methods to randomly generate various aspects of a character,
    including attributes, abilities, and other traits based on the specified
    experience level and campaign settings.

    Args:
        guild_id (int): The ID of the guild where the character is being generated.
        user (User): The user for whom the character is being generated.
        experience_level (RNGCharLevel, optional): The experience level for character generation.
            Defaults to a random level if not specified.
        campaign (Campaign, optional): The campaign associated with the character.
            Defaults to None.

    Attributes:
        ctx (ValentinaContext): The context of the Discord application.
        user (User): The user for whom the character is being generated.
        experience_level (RNGCharLevel): The experience level for character generation.
        campaign (Campaign): The campaign associated with the character, if any.
    """

    def __init__(
        self,
        user: User,
        guild_id: int,
        experience_level: RNGCharLevel = None,
        campaign: Campaign = None,
    ) -> None:
        self.guild_id = guild_id
        self.user = user
        self.experience_level = experience_level or RNGCharLevel.random_member()
        self.campaign = campaign

    @staticmethod
    def _redistribute_trait_values(
        traits: list[CharacterTrait], concept: CharacterConcept
    ) -> list[CharacterTrait]:
        """Redistribute trait values based on the character concept.

        Ensure that specific traits associated with a concept have high values by
        redistributing points from less important traits. The redistribution process
        continues until all concept-specific traits have a value of at least 3, or
        until no more redistribution is possible.

        Args:
            traits (list[CharacterTrait]): The list of traits to redistribute.
            concept (CharacterConcept): The character concept to use for redistribution.

        Returns:
            list[CharacterTrait]: The updated list of CharacterTrait objects after redistribution.
        """
        while any(
            t
            for t in traits
            if t.name in concept.value.specific_abilities and t.value < 3  # noqa: PLR2004
        ):
            # Stop iterating if there are no dots to be redistributed
            if not any(
                x for x in traits if x.name not in concept.value.specific_abilities and x.value >= 1
            ):
                break

            # Subtract 1 from the lowest value non-specific trait.
            unimportant_trait = next(
                x for x in traits if x.name not in concept.value.specific_abilities and x.value >= 1
            )
            unimportant_trait.value -= 1

            # Add 1 to the lowest value specific trait
            specified_trait = next(
                x
                for x in traits
                if x.name in concept.value.specific_abilities and x.value < 3  # noqa: PLR2004
            )
            specified_trait.value += 1

        return traits

    def _adjust_value_based_on_level(self, value: int) -> int:
        """Adjust the discipline value based on the character's experience level.

        Modify the given discipline value according to the character's experience level.
        Increment the value for advanced and elite levels, cap it for new and intermediate
        characters, and ensure the final value is within the valid range.

        Args:
            value (int): The initial discipline value.

        Returns:
            int: The adjusted discipline value, constrained between 1 and 5.
        """
        # Increment value for advanced and elite levels
        if self.experience_level in {RNGCharLevel.ADVANCED, RNGCharLevel.ELITE}:
            value += 1

        # Cap values based on character level
        if self.experience_level == RNGCharLevel.NEW and value > 2:  # noqa: PLR2004
            value = 2

        if self.experience_level == RNGCharLevel.INTERMEDIATE and value > 3:  # noqa: PLR2004
            value = 3

        # Constrain the final value between 1 and 5
        return max(min(value, 5), 1)

    async def generate_base_character(
        self,
        char_class: CharClass | None = None,
        concept: CharacterConcept | None = None,
        clan: VampireClan | None = None,
        creed: HunterCreed | None = None,
        player_character: bool = False,
        storyteller_character: bool = False,
        developer_character: bool = False,
        chargen_character: bool = False,
        gender: Literal["male", "female"] | None = None,
        nationality: str = "us",
        nickname_is_class: bool = False,
    ) -> Character:
        """Generate a base character with random attributes.

        Generate a base character with randomly selected attributes including class,
        concept, clan (for vampires), creed (for hunters), and name. Traits and
        customizations are not included in this base generation.

        Args:
            char_class (CharClass | None): Specific character class. If None, randomly selected.
            concept (CharacterConcept | None): Specific character concept. If None, randomly selected.
            clan (VampireClan | None): Specific vampire clan. If None, randomly selected for vampires.
            creed (HunterCreed | None): Specific hunter creed. If None, randomly selected for hunters.
            player_character (bool): Whether the character is a player character.
            storyteller_character (bool): Whether the character is a storyteller character.
            developer_character (bool): Whether the character is a developer character.
            chargen_character (bool): Whether the character is generated through character generation.
            gender (Literal["male", "female"] | None): Gender for name generation.
            nationality (str): Nationality for name generation. Defaults to "us".
            nickname_is_class (bool): Whether to use the class name as a nickname.

        Returns:
            Character: The generated base character.
        """
        # Grab random name
        name_first, name_last = await fetch_random_name(gender=gender, country=nationality)

        # Grab a random class
        if char_class is None:
            percentile = random_num(100)
            char_class = CharClass.get_member_by_value(percentile)

        name_nick = char_class.value.name if nickname_is_class else None

        # Grab a random concept
        if concept is None:
            percentile = random_num(100)
            concept = CharacterConcept.get_member_by_value(percentile)

        # Grab class specific information
        if char_class == CharClass.VAMPIRE and not clan:
            clan = VampireClan.random_member()

        if char_class == CharClass.HUNTER and not creed:
            percentile = random_num(100)
            creed = HunterCreed.get_member_by_value(percentile)

        character = Character(
            name_first=name_first,
            name_last=name_last,
            name_nick=name_nick,
            char_class_name=char_class.name,
            concept_name=concept.name,
            clan_name=clan.name if clan else None,
            creed_name=creed.name if creed else None,
            guild=self.guild_id,
            type_chargen=chargen_character,
            type_player=player_character,
            type_storyteller=storyteller_character,
            type_developer=developer_character,
            user_creator=self.user.id,
            user_owner=self.user.id,
            campaign=str(self.campaign.id) if self.campaign else None,
        )

        await character.insert()
        return character

    async def generate_full_character(
        self,
        char_class: CharClass | None = None,
        concept: CharacterConcept | None = None,
        clan: VampireClan | None = None,
        creed: HunterCreed | None = None,
        player_character: bool = False,
        storyteller_character: bool = False,
        developer_character: bool = False,
        chargen_character: bool = False,
        gender: Literal["male", "female"] | None = None,
        nationality: str = "us",
        nickname_is_class: bool = False,
    ) -> Character:
        """Generate a full character with random values.

        Generate a complete character with randomized values for all traits and abilities,
        and add it to the database. This method is primarily used by Storytellers for
        quick NPC creation.

        Args:
            char_class (CharClass | None): The character's class. If None, a random class is chosen.
            concept (CharacterConcept | None): The character's concept. If None, a random concept is chosen.
            clan (VampireClan | None): The character's clan (for vampires). If None, a random clan is chosen.
            creed (HunterCreed | None): The character's creed (for hunters). If None, a random creed is chosen.
            player_character (bool): Whether this is a player character. Defaults to False.
            storyteller_character (bool): Whether this is a storyteller character. Defaults to False.
            developer_character (bool): Whether this is a developer character. Defaults to False.
            chargen_character (bool): Whether this character was created through character generation. Defaults to False.
            gender (Literal["male", "female"] | None): The character's gender. If None, a random gender is chosen.
            nationality (str): The character's nationality. Defaults to "us".
            nickname_is_class (bool): Whether to use the character's class as their nickname. Defaults to False.

        Returns:
            Character: The fully generated character object.
        """
        filtered_locals = {k: v for k, v in locals().items() if k != "self"}

        character = await self.generate_base_character(**filtered_locals)
        character = await self.random_attributes(character)
        character = await self.random_abilities(character)
        character = await self.random_disciplines(character)
        character = await self.random_virtues(character)
        character = await self.random_backgrounds(character)
        character = await self.random_willpower(character)
        character = await self.random_hunter_traits(character)
        return await self.concept_special_abilities(character)

    async def random_attributes(self, character: Character) -> Character:
        """Randomly generate attributes for the character.

        Generate and assign random attribute values for the given character based on their
        concept, class, and experience level. This method handles the distribution of
        attribute dots across physical, social, and mental categories.

        Args:
            character (Character): The character for which to generate attributes.

        Returns:
            Character: The updated character object with randomly generated attributes.
        """
        logger.debug(f"Generate attribute values for {character.name}")

        concept = CharacterConcept[character.concept_name] if character.concept_name else None
        char_class = CharClass[character.char_class_name]

        # Initialize dot distribution based on character level
        starting_dot_distribution = (
            [9, 8, 6] if char_class in {CharClass.MORTAL, CharClass.HUNTER} else [10, 8, 6]
        )
        extra_dots_map = {
            RNGCharLevel.NEW: [0, 0, 0],
            RNGCharLevel.INTERMEDIATE: [1, 0, 0],
            RNGCharLevel.ADVANCED: [2, 1, 0],
            RNGCharLevel.ELITE: [3, 2, 1],
        }
        total_dots = [
            a + b
            for a, b in zip(
                starting_dot_distribution, extra_dots_map[self.experience_level], strict=True
            )
        ]

        # Initialize category priority
        attributes = [TraitCategory.PHYSICAL, TraitCategory.SOCIAL, TraitCategory.MENTAL]

        primary_category = (
            concept.value.attribute_specialty if concept else random.choice(attributes)
        )
        attributes.remove(primary_category)
        secondary_category = random.choice(attributes)
        attributes.remove(secondary_category)
        tertiary_category = random.choice(attributes)

        # Assign dots to each attribute
        for cat in [primary_category, secondary_category, tertiary_category]:
            category_dots = total_dots.pop(0)

            category_traits = cat.get_trait_list(CharClass[character.char_class_name])

            trait_values = divide_total_randomly(category_dots, len(category_traits), 5, 1)

            # Create the attributes and assign them to the character
            for t in category_traits:
                trait = CharacterTrait(
                    name=t,
                    value=trait_values.pop(0),
                    max_value=get_max_trait_value(t, cat.name),
                    character=str(character.id),
                    category_name=cat.name,
                )

                await trait.insert()

                character.traits.append(trait)

        await character.save()
        return character

    async def random_abilities(self, character: Character) -> Character:
        """Randomly generate abilities for the character.

        This method creates and assigns random ability values to the given character,
        taking into account the character's concept and experience level.

        Args:
            character (Character): The character for which to generate abilities.

        Returns:
            Character: The updated character with randomly generated abilities.
        """
        logger.debug(f"Generate ability values for {character.name}")

        concept = CharacterConcept[character.concept_name] if character.concept_name else None

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
            for a, b in zip(
                starting_dot_distribution, extra_dots_map[self.experience_level], strict=True
            )
        ]

        # Initialize category priority
        abilities = [TraitCategory.TALENTS, TraitCategory.SKILLS, TraitCategory.KNOWLEDGES]

        primary_category = concept.value.ability_specialty if concept else random.choice(abilities)
        abilities.remove(primary_category)
        secondary_category = random.choice(abilities)
        abilities.remove(secondary_category)
        tertiary_category = random.choice(abilities)

        # Assign dots to each attribute
        for cat in [primary_category, secondary_category, tertiary_category]:
            category_dots = total_dots.pop(0)

            category_traits = cat.get_trait_list(CharClass[character.char_class_name])
            trait_values = divide_total_randomly(category_dots, len(category_traits), 5, 0)

            # Create the attributes and assign them to the character
            traits = [
                CharacterTrait(
                    name=t,
                    value=trait_values.pop(0),
                    max_value=get_max_trait_value(t, cat.name),
                    character=str(character.id),
                    category_name=cat.name,
                )
                for t in category_traits
            ]

            traits = self._redistribute_trait_values(traits, concept)

            for trait in traits:
                await trait.insert()
                character.traits.append(trait)

        await character.save()
        return character

    async def random_disciplines(self, character: Character) -> Character:
        """Randomly generate disciplines for the character.

        Generate and assign random discipline values for a given character based on their clan
        and experience level. This method handles the logic for determining which disciplines
        to assign and their values.

        Args:
            character (Character): The character for which to generate disciplines.

        Returns:
            Character: The character with updated disciplines.
        """
        logger.debug(f"Generate discipline values for {character.name}")

        # TODO: Work with Ghouls which have no clan
        try:
            clan = VampireClan[character.clan_name]
        except KeyError:
            return character

        extra_disciplines_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 1,
            RNGCharLevel.ADVANCED: 2,
            RNGCharLevel.ELITE: 3,
        }

        disciplines_to_set = clan.value.disciplines
        other_disciplines = TraitCategory.DISCIPLINES.get_trait_list(
            CharClass[character.char_class_name]
        )
        disciplines_to_set.extend(
            random.sample(
                [x for x in other_disciplines if x not in disciplines_to_set],
                extra_disciplines_map.get(self.experience_level, 0),
            )
        )

        # Generate trait values from a normal distribution
        mean, distribution = self.experience_level.value
        values = [
            self._adjust_value_based_on_level(x)
            for x in _rng.normal(mean, distribution, len(disciplines_to_set)).astype(int32)
        ]

        # Create the attributes and assign them to the character
        for t in disciplines_to_set:
            trait = CharacterTrait(
                name=t,
                value=values.pop(0),
                max_value=get_max_trait_value(t, TraitCategory.DISCIPLINES.name),
                character=str(character.id),
                category_name=TraitCategory.DISCIPLINES.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def random_virtues(self, character: Character) -> Character:
        """Randomly generate virtues for the character.

        Generate and assign random virtue values for the given character based on their
        character class and the current experience level. The method calculates the total
        number of dots to distribute among virtues and assigns them randomly.

        Args:
            character (Character): The character for which to generate virtues.

        Returns:
            Character: The updated character with newly generated virtue traits.
        """
        logger.debug(f"Generate virtue values for {character.name}")

        if not (
            virtues := TraitCategory.VIRTUES.get_trait_list(CharClass[character.char_class_name])
        ):
            return character

        starting_dots = 7
        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 1,
            RNGCharLevel.ELITE: 2,
        }
        total_dots = starting_dots + extra_dots_map[self.experience_level]

        # Divide total dots to produce a value for each attribute
        values = divide_total_randomly(total_dots, len(virtues), max_value=5, min_value=1)

        # Create the traits and assign them to the character
        for v in virtues:
            trait = CharacterTrait(
                name=v,
                value=values.pop(0),
                max_value=get_max_trait_value(v, TraitCategory.VIRTUES.name),
                character=str(character.id),
                category_name=TraitCategory.VIRTUES.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def random_backgrounds(self, character: Character) -> Character:
        """Generate random backgrounds for the character.

        Generate and assign random background values for the given character based on their
        character class and the current experience level. The method calculates the total
        number of dots to distribute among backgrounds and assigns them randomly.

        Args:
            character (Character): The character for which to generate backgrounds.

        Returns:
            Character: The updated character with newly generated background traits.
        """
        logger.debug(f"Generate background values for {character.name}")

        char_class = CharClass[character.char_class_name]

        if not (backgrounds := TraitCategory.BACKGROUNDS.get_trait_list(char_class)):
            return character

        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 1,
            RNGCharLevel.ADVANCED: 3,
            RNGCharLevel.ELITE: 5,
        }
        total_dots = (
            char_class.value.chargen_background_dots + extra_dots_map[self.experience_level]
        )
        if total_dots == 0:
            return character

        trait_values = divide_total_randomly(total_dots, len(backgrounds), 5, 0)

        # Create the backgrounds and assign them to the character
        for b in backgrounds:
            trait = CharacterTrait(
                name=b,
                value=trait_values.pop(0),
                max_value=get_max_trait_value(b, TraitCategory.BACKGROUNDS.name),
                character=str(character.id),
                category_name=TraitCategory.BACKGROUNDS.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def random_willpower(self, character: Character) -> Character:
        """Randomly generate willpower for the character.

        Generate and assign willpower trait for the character based on their existing
        Self-Control and Courage traits. If applicable, also generate and assign
        a Humanity trait based on the character's Conscience trait.

        Args:
            character (Character): The character for which to generate willpower.

        Returns:
            Character: The updated character with newly generated willpower
                       and potentially humanity traits.
        """
        logger.debug(f"Generate willpower values for {character.name}")

        if not any(x.name for x in character.traits if x.name == "Self-Control"):  # type: ignore [attr-defined]
            return character

        courage = next(
            x for x in cast(list[CharacterTrait], character.traits) if x.name == "Courage"
        )
        self_control = next(
            x for x in cast(list[CharacterTrait], character.traits) if x.name == "Self-Control"
        )
        conscience = next(
            x for x in cast(list[CharacterTrait], character.traits) if x.name == "Conscience"
        )

        willpower = CharacterTrait(
            name="Willpower",
            value=self_control.value + courage.value,
            character=str(character.id),
            category_name=TraitCategory.OTHER.name,
            max_value=10,
        )
        await willpower.insert()
        character.traits.append(willpower)

        if "Humanity" in TraitCategory.OTHER.get_trait_list(character.char_class):
            humanity = CharacterTrait(
                name="Humanity",
                value=conscience.value,
                character=str(character.id),
                category_name=TraitCategory.OTHER.name,
                max_value=10,
            )
            await humanity.insert()
            character.traits.append(humanity)

        await character.save()
        return character

    async def random_hunter_traits(self, character: Character) -> Character:
        """Randomly generate hunter traits for the character.

        Generate and assign hunter-specific traits such as Willpower, Conviction,
        and Edges based on the character's creed and experience level. If the
        character doesn't have a creed, a random one is assigned.

        Args:
            character (Character): The character for which to generate hunter traits.

        Returns:
            Character: The updated character with newly generated hunter traits.
        """
        if character.char_class != CharClass.HUNTER:
            return character

        logger.debug(f"Generate hunter trait values for {character.name}")

        try:
            creed = HunterCreed[character.creed_name]
        except KeyError:
            creed = HunterCreed.random_member()
            character.creed_name = creed.name

        willpower = CharacterTrait(
            name="Willpower",
            value=3,  # Hunter willpower is always 3
            character=str(character.id),
            category_name=TraitCategory.OTHER.name,
            max_value=10,
        )
        await willpower.insert()
        character.traits.append(willpower)

        conviction = CharacterTrait(
            name="Conviction",
            value=creed.value.conviction,
            character=str(character.id),
            category_name=TraitCategory.OTHER.name,
            max_value=get_max_trait_value("Conviction", TraitCategory.OTHER.name),
        )
        await conviction.insert()
        character.traits.append(conviction)

        # Assign Edges
        edges = creed.value.edges
        starting_dots = 5
        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 1,
            RNGCharLevel.ELITE: 2,
        }
        total_dots = starting_dots + extra_dots_map[self.experience_level]
        trait_values = divide_total_randomly(total_dots, len(edges), 5, 0)

        # Create the edges and assign them to the character
        for e in edges:
            trait = CharacterTrait(
                name=e,
                value=trait_values.pop(0),
                max_value=get_max_trait_value(e, TraitCategory.EDGES.name),
                character=str(character.id),
                category_name=TraitCategory.EDGES.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def concept_special_abilities(self, character: Character) -> Character:
        """Assign special abilities based on the character's concept.

        This method assigns special abilities to a character based on their concept,
        but only if the character is a Mortal. For non-Mortal characters, it returns
        the character unchanged.

        Args:
            character (Character): The character to assign special abilities to.

        Returns:
            Character: The updated character with assigned special abilities.
        """
        if character.char_class != CharClass.MORTAL:
            return character

        logger.debug(f"Assign special abilities for {character.name}")

        # Assign Traits
        for ability in character.concept.value.abilities:
            if isinstance(ability["traits"], list):
                for name, value, category in ability["traits"]:
                    trait = CharacterTrait(
                        name=name,
                        value=value,
                        max_value=get_max_trait_value(name, category),
                        character=str(character.id),
                        category_name=category,
                    )
                    await trait.insert()
                    character.traits.append(trait)

            if isinstance(ability["custom_sections"], list):
                character.sheet_sections.extend(
                    [
                        CharacterSheetSection(title=title, content=content)
                        for title, content in ability["custom_sections"]
                    ]
                )
        await character.save()
        return character
