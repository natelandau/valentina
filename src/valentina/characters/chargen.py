"""A RNG character generator for Valentina."""

import random
from typing import Literal, cast

import discord
import inflect
from beanie import DeleteRules
from discord.ext import pages
from discord.ui import Button
from loguru import logger
from numpy import int32
from numpy.random import default_rng

from valentina.constants import (
    CharacterConcept,
    CharClass,
    EmbedColor,
    Emoji,
    HunterCreed,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.models import Campaign, Character, CharacterSheetSection, CharacterTrait, User
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils.helpers import (
    adjust_sum_to_match_total,
    divide_into_three,
    fetch_random_name,
    get_max_trait_value,
)
from valentina.views import ChangeNameModal, sheet_embed

from .reallocate_dots import DotsReallocationWizard
from .spend_experience import SpendFreebiePoints

p = inflect.engine()
p.defnoun("Ability", "Abilities")
_rng = default_rng()


class CharacterPickerButtons(discord.ui.View):
    """Manage buttons for selecting a character in the CharGenWizard paginator.

    Args:
        ctx (ValentinaContext): The context of the Discord application.
        characters (list[Character]): List of characters to choose from.

    Attributes:
        pick_character (bool): Whether a character was picked.
        selected (Character): The selected character.
        reroll (bool): Whether to reroll characters.
        cancelled (bool): Whether the selection was cancelled.
    """

    def __init__(self, ctx: ValentinaContext, characters: list[Character]):
        super().__init__(timeout=3000)
        self.ctx = ctx
        self.characters = characters
        self.pick_character: bool = False
        self.selected: Character = None
        self.reroll: bool = False
        self.cancelled: bool = False

        # Create a button for each character
        for i, character in enumerate(characters):
            button: Button = Button(
                label=f"{i + 1}. {character.full_name}",
                custom_id=f"{i}",
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a character."""
        await interaction.response.defer()
        self._disable_all()
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected = self.characters[index]
        self.pick_character = True
        self.stop()

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Reroll (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="reroll",
        row=2,
    )
    async def reroll_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.reroll = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
        row=2,
    )
    async def cancel_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.cancelled = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class BeginCancelCharGenButtons(discord.ui.View):
    """Manage buttons for initiating or canceling the character generation process.

    Args:
    author (Union[discord.User, discord.Member, None]): The author of the interaction.

    Attributes:
    roll (bool): Whether to roll for characters.
    """

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.roll: bool = None

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Roll Characters (10xp)",
        style=discord.ButtonStyle.success,
        custom_id="roll",
        row=2,
    )
    async def roll_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the roll button."""
        await interaction.response.defer()
        button.label += f" {Emoji.YES.value}"
        self._disable_all()

        self.roll = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
        row=2,
    )
    async def cancel_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the cancel button."""
        await interaction.response.defer()
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        self._disable_all()
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.roll = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id


class UpdateCharacterButtons(discord.ui.View):
    """Manage buttons for updating a character's attributes.

    Args:
        ctx (ValentinaContext): The context of the Discord application.
        character (Character): The character to update.
        author (Union[discord.User, discord.Member, None]): The author of the interaction.

    Attributes:
        updated (bool): Whether the character has been updated.
        done (bool): Whether the update process is done.
    """

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
        author: discord.User | discord.Member | None = None,
    ):
        super().__init__()
        self.ctx = ctx
        self.character = character
        self.author = author
        self.updated: bool = False
        self.done: bool = False

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.PENCIL.value} Rename",
        style=discord.ButtonStyle.primary,
        custom_id="rename",
        row=2,
    )
    async def rename_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the rename button."""
        self._disable_all()

        modal = ChangeNameModal(character=self.character, title="Rename Character")
        await interaction.response.send_modal(modal)
        await modal.wait()

        self.character = modal.character
        self.updated = True
        self.stop()

    @discord.ui.button(
        label="💪 Reallocate Dots",
        style=discord.ButtonStyle.primary,
        custom_id="reallocate",
        row=2,
    )
    async def reallocate_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the reallocate button."""
        await interaction.response.defer()
        self._disable_all()

        dot_wizard = DotsReallocationWizard(self.ctx, self.character)
        updated, character = await dot_wizard.start_wizard()
        if updated:
            self.character = character

        self.updated = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Done Reallocating Dots",
        style=discord.ButtonStyle.success,
        custom_id="done",
        row=3,
    )
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the done button."""
        await interaction.response.defer()
        button.disabled = True
        self._disable_all()
        self.done = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class FreebiePointsButtons(discord.ui.View):
    """Manage buttons for spending freebie points."""

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
    ):
        super().__init__()
        self.ctx = ctx
        self.character = character
        self.updated: bool = False
        self.done: bool = False

        button: Button = Button(
            label=f"💪 Spend {self.character.freebie_points} Freebie Points",
            style=discord.ButtonStyle.primary,
            custom_id="freebie_points",
            row=2,
        )
        button.callback = self.freebie_callback  # type: ignore [method-assign]
        self.add_item(button)

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def freebie_callback(self, interaction: discord.Interaction) -> None:
        """Callback for the reallocate button."""
        await interaction.response.defer()
        self._disable_all()

        freebie_wizard = SpendFreebiePoints(self.ctx, self.character)
        updated, character = await freebie_wizard.start_wizard()
        if updated:
            self.character = character

        self.updated = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Done Spending Freebie Points",
        style=discord.ButtonStyle.success,
        custom_id="done",
        row=3,
    )
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the done button."""
        await interaction.response.defer()
        button.disabled = True
        self._disable_all()
        self.done = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class RNGCharGen:
    """Randomly generate different parts of a character."""

    def __init__(
        self, ctx: ValentinaContext, user: User, experience_level: RNGCharLevel = None
    ) -> None:
        self.ctx = ctx
        self.user = user
        self.experience_level = (
            experience_level if experience_level else RNGCharLevel.random_member()
        )

    @staticmethod
    def _redistribute_trait_values(
        traits: list[CharacterTrait], concept: CharacterConcept
    ) -> list[CharacterTrait]:
        """Redistribute trait values based on the concept. This method ensures that specific traits associated with a concept have high values for the specified traits.

        Args:
            traits (list[CharacterTrait]): The traits to redistribute.
            concept (CharacterConcept): The concept to use for redistribution.

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
        """Generate's the base character based on random values.

        A base character consists of a combination of the following:

        - A random class
        - A random concept
        - A random clan (if applicable)
        - A random creed (if applicable)
        - A random name

        Traits and customizations are to be added later.

        Returns:
            Character: The generated character.
        """
        # Grab random name
        name_first, name_last = await fetch_random_name(gender=gender, country=nationality)

        # Grab a random class
        if char_class is None:
            percentile = _rng.integers(1, 101)
            char_class = CharClass.get_member_by_value(percentile)

        name_nick = char_class.value.name if nickname_is_class else None

        # Grab a random concept
        if concept is None:
            percentile = _rng.integers(1, 101)
            concept = CharacterConcept.get_member_by_value(percentile)

        # Grab class specific information
        if char_class == CharClass.VAMPIRE and not clan:
            clan = VampireClan.random_member()

        if char_class == CharClass.HUNTER and not creed:
            percentile = _rng.integers(1, 101)
            creed = HunterCreed.get_member_by_value(percentile)

        character = Character(
            name_first=name_first,
            name_last=name_last,
            name_nick=name_nick,
            char_class_name=char_class.name,
            concept_name=concept.name,
            clan_name=clan.name if clan else None,
            creed_name=creed.name if creed else None,
            guild=self.ctx.guild.id,
            type_chargen=chargen_character,
            type_player=player_character,
            type_storyteller=storyteller_character,
            type_developer=developer_character,
            user_creator=self.user.id,
            user_owner=self.user.id,
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
        """Generate a full character with random values."""
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

        Args:
            character (Character): The character for which to generate attributes.
        """
        logger.debug(f"CHARGEN: Generate attribute values for {character.name}")

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

            # Generate initial random distribution for the traits in the category
            mean, distribution = self.experience_level.value
            random_values = [
                max(min(x, 5), 0)
                for x in _rng.normal(mean, distribution, len(category_traits)).astype(int32)
            ]

            # Adjust the sum of the list to match the total dots for the category
            final_values = adjust_sum_to_match_total(
                random_values, category_dots, max_value=5, min_value=1
            )

            # Create the attributes and assign them to the character
            for t in category_traits:
                trait = CharacterTrait(
                    name=t,
                    value=final_values.pop(0),
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

        Args:
            character (Character): The character for which to generate abilities.
        """
        logger.debug(f"CHARGEN: Generate ability values for {character.name}")

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

            # Generate initial random distribution for the traits in the category
            mean, distribution = self.experience_level.value
            random_values = [
                max(min(x, 5), 0)
                for x in _rng.normal(mean, distribution, len(category_traits)).astype(int32)
            ]

            # Adjust the sum of the list to match the total dots for the category
            final_values = adjust_sum_to_match_total(random_values, category_dots, max_value=5)

            # Create the attributes and assign them to the character
            traits = [
                CharacterTrait(
                    name=t,
                    value=final_values.pop(0),
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

        Args:
            character (Character): The character for which to generate disciplines.

        Returns:
            Character: The updated character.
        """
        logger.debug(f"CHARGEN: Generate discipline values for {character.name}")

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

        Args:
            character (Character): The character for which to generate virtues.

        Returns:
            Character: The updated character.
        """
        logger.debug(f"CHARGEN: Generate virtue values for {character.name}")

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

        # Divide total dots for each category into three to produce a value for each attribute
        dots_for_each = divide_into_three(total_dots)

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(dots_for_each, total_dots, max_value=5, min_value=1)

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
        """Randomly generate backgrounds for the character.

        Args:
            character (Character): The character for which to generate backgrounds.

        Returns:
            Character: The updated character.
        """
        logger.debug(f"CHARGEN: Generate background values for {character.name}")

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

        # Generate initial random distribution for the traits in the category
        mean, distribution = self.experience_level.value
        initial_values = [
            max(min(x, 5), 0)
            for x in _rng.normal(mean, distribution, len(backgrounds)).astype(int32)
        ]

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(initial_values, total_dots, max_value=5)

        # Create the backgrounds and assign them to the character
        for b in backgrounds:
            trait = CharacterTrait(
                name=b,
                value=values.pop(0),
                max_value=get_max_trait_value(b, TraitCategory.BACKGROUNDS.name),
                character=str(character.id),
                category_name=TraitCategory.BACKGROUNDS.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def random_willpower(self, character: Character) -> Character:  # noqa: PLR6301
        """Randomly generate willpower for the character.

        Args:
            character (Character): The character for which to generate willpower.

        Returns:
            Character: The updated character.
        """
        logger.debug(f"CHARGEN: Generate willpower values for {character.name}")

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

        Args:
            character (Character): The character for which to generate hunter traits.

        Returns:
            Character: The updated character.
        """
        if character.char_class != CharClass.HUNTER:
            return character

        logger.debug(f"CHARGEN: Generate hunter trait values for {character.name}")

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
            value=creed.value["conviction"],
            character=str(character.id),
            category_name=TraitCategory.OTHER.name,
            max_value=get_max_trait_value("Conviction", TraitCategory.OTHER.name),
        )
        await conviction.insert()
        character.traits.append(conviction)

        # Assign Edges
        edges = creed.value["edges"]
        starting_dots = 5
        extra_dots_map = {
            RNGCharLevel.NEW: 0,
            RNGCharLevel.INTERMEDIATE: 0,
            RNGCharLevel.ADVANCED: 1,
            RNGCharLevel.ELITE: 2,
        }
        total_dots = starting_dots + extra_dots_map[self.experience_level]

        # Generate initial random distribution for the traits in the category
        mean, distribution = self.experience_level.value
        initial_values = [
            max(min(x, 3), 0) for x in _rng.normal(mean, distribution, len(edges)).astype(int32)
        ]

        # Adjust the sum of the list to match the total dots for the category
        values = adjust_sum_to_match_total(values=initial_values, total=total_dots, max_value=3)

        # Create the edges and assign them to the character
        for e in edges:
            trait = CharacterTrait(
                name=e,
                value=values.pop(0),
                max_value=get_max_trait_value(e, TraitCategory.EDGES.name),
                character=str(character.id),
                category_name=TraitCategory.EDGES.name,
            )
            await trait.insert()
            character.traits.append(trait)

        await character.save()
        return character

    async def concept_special_abilities(self, character: Character) -> Character:  # noqa: PLR6301
        """Assign special abilities based on the character's concept.

        Args:
            character (Character): The character for which to assign special abilities.

        Returns:
            Character: The updated character.
        """
        if character.char_class != CharClass.MORTAL:
            return character

        logger.debug(f"CHARGEN: Assign special abilities for {character.name}")

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


class CharGenWizard:
    """Guide the user through a step-by-step character generation process.

    Args:
        ctx (ValentinaContext): The context of the Discord application.
        campaign (Campaign): The campaign for which the character is being created.
        user (GuildUser): The user who is creating the character.
        hidden (bool, optional): Whether the interaction is hidden. Defaults to True.

    Attributes:
        paginator (pages.Paginator): Container for the paginator.
    """

    # TODO: Allow the user to select their special ability when a choice is available
    # TODO: Edges for hunters
    # TODO: Improve mages, changelings, werewolves, and ghouls

    def __init__(
        self,
        ctx: ValentinaContext,
        campaign: Campaign,
        user: User,
        experience_level: RNGCharLevel = None,
        hidden: bool = True,
    ) -> None:
        self.ctx = ctx
        self.interaction = ctx.interaction
        self.bot = cast(Valentina, ctx.bot)

        self.user = user
        self.campaign = campaign
        self.experience_level = experience_level
        self.hidden = hidden

        self.paginator: pages.Paginator = None  # Initialize paginator to None
        self.engine = RNGCharGen(ctx, user, experience_level)

    @staticmethod
    def _special_ability_char_sheet_text(character: Character) -> str:
        """Generate the special abilities text for the character sheet."""
        # Extract concept information for mortals
        if character.char_class.name == CharClass.MORTAL.name:
            concept_info = CharacterConcept[character.concept_name].value

            # Generate special abilities list
            special_abilities = [
                f"{i}. **{ability['name']}:** {ability['description']}\n"
                for i, ability in enumerate(concept_info.abilities, start=1)
            ]

            return f"""
    **{character.name} is a {concept_info.name}**
    {concept_info.description}

    **Special {p.plural_noun("Ability", len(concept_info.abilities))}: **
    {"".join(special_abilities)}
    """
        # Return None unless the character is a mortal
        return None

    async def _generate_character_sheet_embed(
        self,
        character: Character,
        title: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> discord.Embed:
        """Create an embed for the character sheet.

        Args:
            character (Character): The character for which to create the embed.
            title (str | None, optional): The title of the embed. Defaults to None.
            prefix (str | None, optional): The prefix for the description. Defaults to None.
            suffix (str | None, optional): The suffix for the description. Defaults to None.

        Returns:
            discord.Embed: The created embed.
        """
        # Create the embed
        return await sheet_embed(
            self.ctx,
            character,
            title=title if title else f"{character.name}",
            desc_prefix=prefix,
            desc_suffix=suffix,
            show_footer=False,
        )

    async def _cancel_character_generation(self, msg: str | None = None) -> None:
        """Cancel the character generation process.

        Args:
            msg (str, optional): Message to display. Defaults to None.
        """
        if not msg:
            msg = "No character was created."

        embed = discord.Embed(
            title=f"{Emoji.CANCEL.value} Cancelled",
            description=msg,
            color=EmbedColor.WARNING.value,
        )
        embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
        await self.paginator.cancel(page=embed, include_custom=True)

    async def start(self, restart: bool = False) -> None:
        """Initiate the character generation wizard.

        Args:
            restart (bool, optional): Whether to restart the wizard. Defaults to False.
        """
        logger.debug("CHARGEN: Starting the character generation wizard.")

        # Build the instructional embeds
        embed1 = discord.Embed(
            title="Create a new character",
            description="""\
For the cost of 10xp, I will generate three characters for you to choose between.  You select the one you want to keep.
### How this works
By rolling percentile dice we select a class and a concept.  The concept guides how default dots are added to your character.

Once you select a character you can re-allocate dots and change the name, but you cannot change the concept, class, or clan.

*View the possible classes and concepts by scrolling through the pages below*
""",
            color=EmbedColor.INFO.value,
        )
        embed2 = discord.Embed(
            title="Classes",
            description="\n".join(
                [
                    f"- **`{c.value.percentile_range[1] - c.value.percentile_range[0]}%` {c.value.name}** {c.value.description}"
                    for c in CharClass.playable_classes()
                ]
            ),
            color=EmbedColor.INFO.value,
        )
        embed3 = discord.Embed(
            title="Concepts",
            description="\n".join(
                [
                    f"- **{c.value.name}** {c.value.description}"
                    for c in CharacterConcept
                    if c.value.percentile_range is not None
                ]
            ),
            color=EmbedColor.INFO.value,
        )

        # Create and display the paginator
        view = BeginCancelCharGenButtons(self.ctx.author)
        if restart:
            await self.paginator.update(pages=[embed1, embed2, embed3], custom_view=view)  # type: ignore [arg-type]
        else:
            self.paginator = pages.Paginator(
                pages=[embed1, embed2, embed3],  # type: ignore [arg-type]
                custom_view=view,
                author_check=True,
                timeout=600,
            )
            self.paginator.remove_button("first")
            self.paginator.remove_button("last")
            await self.paginator.respond(self.ctx.interaction, ephemeral=self.hidden)

        await view.wait()

        if not view.roll:
            await self._cancel_character_generation()
            return

        # Spend 10 XP
        await self.user.spend_campaign_xp(self.campaign, 10)

        # Move on reviewing three options
        await self.present_character_choices()

    async def present_character_choices(self) -> None:
        """Guide the user through the character selection process.

        This method generates three random characters for the user to choose from.
        It then presents these characters using a paginator. The user can either
        select a character, reroll for new characters, or cancel the process.

        Returns:
            None: This method returns nothing.
        """
        logger.debug("CHARGEN: Starting the character selection process")

        # Generate 3 characters
        characters = [
            await self.engine.generate_base_character(chargen_character=True) for _ in range(3)
        ]

        # TODO: Add traits to each character
        for character in characters:
            await self.engine.random_attributes(character)
            await self.engine.random_abilities(character)
            await self.engine.random_disciplines(character)
            await self.engine.random_virtues(character)
            await self.engine.random_backgrounds(character)
            await self.engine.random_willpower(character)
            await self.engine.random_hunter_traits(character)
            await self.engine.concept_special_abilities(character)

        # Add the pages to the paginator
        description = f"## Created {len(characters)} {p.plural_noun('character', len(characters))} for you to choose from\n"
        character_list = [
            f"{i}. **{c.name}:**  A {CharacterConcept[c.concept_name].value.name} {VampireClan[c.clan_name].value.name if c.clan_name else ''} {CharClass[c.char_class.name].value.name}"
            for i, c in enumerate(characters)
        ]
        description += "\n".join(character_list)
        description += """
### Next Steps
1. **Review the details for each character** by scrolling through their sheets
2. **Select the character you want to play** by selecting a button below; or
3. **Reroll all characters** by selecting the reroll button for a cost of `10 XP`

**Important:**
Once you select a character you can re-allocate dots and change the name, but you cannot change the concept, class, or clan.
"""

        pages: list[discord.Embed] = [
            discord.Embed(
                title="Character Generations", description=description, color=EmbedColor.INFO.value
            )
        ]
        pages.extend(
            [
                await self._generate_character_sheet_embed(
                    character, suffix=self._special_ability_char_sheet_text(character)
                )
                for character in characters
            ]
        )

        # present the character selection paginator
        view = CharacterPickerButtons(self.ctx, characters)
        await self.paginator.update(
            pages=pages,  # type: ignore [arg-type]
            custom_view=view,
            timeout=600,
        )
        await view.wait()

        if view.cancelled:
            await self._cancel_character_generation(
                msg="No character was created but you lost 10 XP for wasting my time."
            )
            return

        if view.reroll:
            campaign_xp, _, _ = self.user.fetch_campaign_xp(self.campaign)

            # Delete the previously created characters
            logger.debug("CHARGEN: Rerolling characters and deleting old ones.")
            for character in characters:
                await character.delete(link_rule=DeleteRules.DELETE_LINKS)

            # Check if the user has enough XP to reroll
            if campaign_xp < 10:  # noqa: PLR2004
                await self._cancel_character_generation(msg="Not enough XP to reroll")
                return

            # Restart the character generation process
            await self.start(restart=True)

        if view.pick_character:
            selected_character = view.selected

            for c in characters:
                if c.id != selected_character.id:
                    # Delete the characters the user did not select
                    await c.delete(link_rule=DeleteRules.DELETE_LINKS)

                if c.id == selected_character.id:
                    # Add the player into the database
                    c.freebie_points = 21
                    c.type_player = True
                    c.type_chargen = False
                    await c.save()

                    self.user.characters.append(c)
                    await self.user.save()

                    selected_character = c

            # Post-process the character
            await self.finalize_character_selection(selected_character)

    async def finalize_character_selection(self, character: Character) -> None:
        """Review and finalize the selected character.

        This method presents the user with an updated character sheet.
        The user can either finalize the character or make additional changes.

        Args:
            character (Character): The selected character to review.
        """
        logger.debug(f"CHARGENL Update the character: {character.full_name}")

        # Create the character sheet embed
        title = f"{Emoji.YES.value} Created {character.full_name}\n"
        embed = await self._generate_character_sheet_embed(
            character, title=title, suffix=self._special_ability_char_sheet_text(character)
        )

        # Update the paginator
        view = UpdateCharacterButtons(self.ctx, character=character, author=self.ctx.author)
        await self.paginator.update(
            pages=[embed],  # type: ignore [arg-type]
            custom_view=view,
            show_disabled=False,
            show_indicator=False,
            timeout=600,
        )

        await view.wait()
        if view.updated:
            # Restart the view and show the changes
            await self.finalize_character_selection(view.character)

        if view.done:
            await self.spend_freebie_points(character)

    async def spend_freebie_points(self, character: Character) -> Character:
        """Spend freebie points.

        Args:
            character (Character): The character for which to spend freebie points.

        Returns:
            Character: The created character.
        """
        logger.debug(f"CHARGEN: Spending freebie points for {character.name}")

        # Create the character sheet embed
        title = f"Spend freebie points on {character.name}\n"
        suffix = f"Use the buttons below to chose where you want to spend your `{character.freebie_points}` remaining freebie points.\n"
        embed = await self._generate_character_sheet_embed(character, title=title, suffix=suffix)

        # Update the paginator
        view = FreebiePointsButtons(self.ctx, character=character)
        await self.paginator.update(
            pages=[embed],  # type: ignore [arg-type]
            custom_view=view,
            show_disabled=False,
            show_indicator=False,
            timeout=600,
        )

        await view.wait()
        if view.updated:
            # Restart the view and show the changes
            await self.spend_freebie_points(view.character)

        if view.done:
            # End the wizard
            embed = discord.Embed(
                title=f"{Emoji.SUCCESS.value} Created {character.name}",
                description="Thanks for using my character generation wizard.",
                color=EmbedColor.SUCCESS.value,
            )
            embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
            await self.paginator.cancel(page=embed, include_custom=True)

        return character
