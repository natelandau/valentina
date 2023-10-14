# type: ignore
"""Test the CharacterService class."""

from random import randint
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import discord
import pytest
from dirty_equals import IsList, IsPartialDict

from valentina.constants import (
    CharClassType,
    CharConcept,
    CharSheetSection,
    RNGCharLevel,
    TraitCategories,
    VampireClanType,
)
from valentina.models import CharacterService
from valentina.models.characters import CharacterTraitRandomizer
from valentina.models.db_tables import (
    Character,
    CharacterClass,
    CustomTrait,
    GuildUser,
    Trait,
    TraitCategory,
    TraitClass,
    TraitValue,
    VampireClan,
)
from valentina.models.traits import TraitService
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestCharacterTraitRandomizer:
    """Test the CharacterTraitRandomizer."""

    trait_svc = TraitService()

    @staticmethod
    def _create_character() -> Character:
        """Create a character."""
        character = Character.create(
            owned_by_id=1,
            created_by_id=1,
            guild_id=1,
            char_class_id=1,
            data={
                "first_name": "Test",
                "last_name": "Character",
                "player_character": True,
            },
        )
        return character.set_default_data_values()

    @pytest.mark.parametrize(
        (
            "char_class",
            "concept",
            "level",
            "primary_dots",
            "non_primary_dots",
        ),
        [
            (
                "WEREWOLF",
                "SOLDIER",
                "NEW",
                13,
                [9, 5],
            ),
            (
                "MORTAL",
                "SHAMAN",
                "INTERMEDIATE",
                18,
                [12, 6],
            ),
            (
                "GHOUL",
                "CRUSADER",
                "ADVANCED",
                23,
                [15, 8],
            ),
            (
                "VAMPIRE",
                "UNDER_WORLDER",
                "ELITE",
                28,
                [18, 10],
            ),
        ],
    )
    def test__set_abilities(
        self,
        mock_ctx,
        char_class,
        concept,
        level,
        primary_dots,
        non_primary_dots,
    ) -> None:
        """Test setting abilities."""
        # GIVEN a character
        character = self._create_character()
        character.char_class = CharacterClass.get(CharacterClass.name == char_class)
        character.save()

        # Mock the fetch_all_class_traits method
        all_class_traits = self.trait_svc.fetch_all_class_traits(CharClassType[char_class])
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        # Instantiate the CharacterTraitRandomizer class
        rng = CharacterTraitRandomizer(
            ctx=mock_ctx,
            character=character,
            concept=CharConcept[concept],
            level=RNGCharLevel[level],
        )

        # WHEN we set the abilities
        categories = [
            tc for tc in TraitCategories if tc.value["section"] == CharSheetSection.ABILITIES
        ]
        result = rng._randomly_assign_abilities(categories=categories)

        # THEN assert categories have the correct number of dots
        for category in categories:
            if category == CharConcept[concept].value["ability_specialty"]:
                assert (
                    sum([x[1] for x in result if x[0].category.name == category.name])
                    == primary_dots
                )
            else:
                assert (
                    sum([x[1] for x in result if x[0].category.name == category.name])
                    in non_primary_dots
                )

    @pytest.mark.parametrize(
        (
            "char_class",
            "concept",
            "level",
            "expected_attributes",
            "primary_dots",
            "non_primary_dots",
        ),
        [
            (
                "MORTAL",
                "PERFORMER",
                "NEW",
                ["Charisma", "Manipulation", "Appearance"],
                9,
                [8, 6],
            ),
            (
                "VAMPIRE",
                "BUSINESSMAN",
                "INTERMEDIATE",
                ["Charisma", "Manipulation", "Appearance"],
                11,
                [8, 6],
            ),
            (
                "MORTAL",
                "URBAN_TRACKER",
                "ADVANCED",
                ["Wits", "Perception", "Intelligence"],
                11,
                [9, 6],
            ),
            (
                "WEREWOLF",
                "SOLDIER",
                "ELITE",
                ["Strength", "Dexterity", "Stamina"],
                13,
                [10, 7],
            ),
        ],
    )
    def test__set_attributes(
        self,
        mock_ctx,
        char_class,
        concept,
        level,
        expected_attributes,
        primary_dots,
        non_primary_dots,
    ):
        """Test setting attributes."""
        # GIVEN a character
        character = self._create_character()
        character.char_class = CharacterClass.get(CharacterClass.name == char_class)
        character.save()

        # Mock the fetch_all_class_traits method
        all_class_traits = self.trait_svc.fetch_all_class_traits(CharClassType[char_class])
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        # Instantiate the CharacterTraitRandomizer class
        rng = CharacterTraitRandomizer(
            ctx=mock_ctx,
            character=character,
            concept=CharConcept[concept],
            level=RNGCharLevel[level],
        )

        # WHEN we set the attributes
        result = rng._randomly_assign_attributes(
            categories=[
                tc for tc in TraitCategories if tc.value["section"] == CharSheetSection.ATTRIBUTES
            ]
        )

        # THEN assert the result is correct
        assert len(result) == 9
        assert result[0][0].name in expected_attributes
        assert result[1][0].name in expected_attributes
        assert result[2][0].name in expected_attributes
        assert (result[0][1] + result[1][1] + result[2][1]) == primary_dots
        assert (result[3][1] + result[4][1] + result[5][1]) in non_primary_dots
        assert (result[6][1] + result[7][1] + result[8][1]) in non_primary_dots

    @pytest.mark.parametrize(
        ("char_class", "level", "modifier"),
        [
            ("WEREWOLF", "NEW", 0),
            ("MORTAL", "NEW", 0),
            ("VAMPIRE", "INTERMEDIATE", 0),
            ("VAMPIRE", "ADVANCED", 1),
            ("VAMPIRE", "ELITE", 2),
        ],
    )
    def test__randomly_assign_virtues(self, mock_ctx, char_class, level, modifier) -> None:
        """Test setting virtues."""
        # GIVEN a character
        character = self._create_character()
        character.char_class = CharacterClass.get(CharacterClass.name == char_class)
        character.save()

        # Mock the fetch_all_class_traits method
        all_class_traits = self.trait_svc.fetch_all_class_traits(CharClassType[char_class])
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        # Instantiate the CharacterTraitRandomizer class
        rng = CharacterTraitRandomizer(
            ctx=mock_ctx,
            character=character,
            concept=CharConcept.SOLDIER,  # Ignored for this test
            level=RNGCharLevel[level],
        )

        # WHEN we set the disciplines
        result = rng._randomly_assign_virtues()

        # THEN assert the result is correct
        if char_class != "WEREWOLF":
            assert len(result) == 5
            assert result[0][0].name == "Conscience"
            assert result[1][0].name == "Self-Control"
            assert result[2][0].name == "Courage"
            assert result[3][1] == result[1][1] + result[2][1]
            assert result[4][1] == result[0][1]
            assert result[0][1] + result[1][1] + result[2][1] == 7 + modifier
        else:
            assert not result

    @pytest.mark.parametrize(
        ("char_class", "clan", "level", "clan_disciplines", "num_disciplines"),
        [
            ("VAMPIRE", "BRUJAH", "NEW", ["Celerity", "Potence", "Presence"], 3),
            ("MORTAL", None, "NEW", [], 0),
            ("VAMPIRE", "GIOVANNI", "INTERMEDIATE", ["Dominate", "Necromancy", "Potence"], 4),
            ("VAMPIRE", "MALKAVIAN", "ADVANCED", ["Auspex", "Dominate", "Obfuscate"], 5),
            ("VAMPIRE", "VENTRUE", "ELITE", ["Dominate", "Fortitude", "Presence"], 6),
        ],
    )
    def test__randomly_assign_disciplines(
        self, mock_ctx, char_class, clan, level, clan_disciplines, num_disciplines
    ) -> None:
        """Test setting discipline values."""
        # GIVEN a character
        character = self._create_character()
        character.char_class = CharacterClass.get(CharacterClass.name == char_class)
        if clan:
            character.clan = VampireClan.get(name=clan)

        character.save()

        # Mock the fetch_all_class_traits method
        all_class_traits = self.trait_svc.fetch_all_class_traits(CharClassType[char_class])
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        # Instantiate the CharacterTraitRandomizer class
        rng = CharacterTraitRandomizer(
            ctx=mock_ctx,
            character=character,
            concept=CharConcept.SOLDIER,  # Ignored for this test
            level=RNGCharLevel[level],
        )

        # WHEN we set the disciplines
        result = rng._randomly_assign_disciplines()

        # THEN assert the result is correct
        assert len(result) == num_disciplines
        if num_disciplines > 0:
            assert result[0][0].name == clan_disciplines[0]
            assert result[1][0].name == clan_disciplines[1]
            assert result[2][0].name == clan_disciplines[2]

            for discipline in result:
                assert 1 <= discipline[1] <= 5


@pytest.mark.usefixtures("mock_db")
class TestCharacterModel:
    """Test the character database model."""

    @staticmethod
    def _clear_test_data() -> None:
        """Clear all test data from the database."""
        for character in Character.select():
            if character.id == 1:
                continue
            character.delete_instance(recursive=True, delete_nullable=True)

    @staticmethod
    def test_character_add_custom_trait() -> None:
        """Test the add_custom_trait method.

        GIVEN: A Character object and a TraitCategory object.
        WHEN: The add_custom_trait method is called.
        THEN: The custom trait should be added correctly.
        """
        # GIVEN: A Character object and a TraitCategory object
        test_character = Character.create(
            data={
                "first_name": "add_custom_trait",
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=1,
            created_by=1,
            clan=1,
        )
        assert len(test_character.custom_traits) == 0
        test_category = TraitCategory.get_by_id(1)

        # WHEN: The add_custom_trait method is called
        test_character.add_custom_trait("new_trait", "new description", test_category, 1, 5)

        # THEN: Check the custom trait is added correctly
        assert len(test_character.custom_traits) == 1
        custom_trait = test_character.custom_traits[0]
        assert custom_trait.name == "new_trait"
        assert custom_trait.description == "new description"
        assert custom_trait.category == test_category
        assert custom_trait.value == 1
        assert custom_trait.max_value == 5

        # WHEN: The add_custom_trait method is called again with the same name
        # THEN: Raise a validation error
        with pytest.raises(errors.ValidationError):
            test_character.add_custom_trait("new_trait", "new description", test_category, 1, 5)

    @staticmethod
    def test_character_all_trait_values() -> None:
        """Test the all_trait_values method of the Character class.

        GIVEN: A Character object with traits.
        WHEN: The all_trait_values method is called.
        THEN: All trait values should be returned as a dictionary containing the appropriate tuple values.
        """
        # GIVEN: A Character object with traits
        # (Assuming that the Character with id=1 has the traits as described in the test)

        # WHEN: The all_trait_values method is called
        trait_values = Character.get_by_id(1).all_trait_values

        # THEN: All trait values should be returned as expected
        assert "PHYSICAL" in trait_values
        assert "SKILLS" in trait_values

        assert trait_values["PHYSICAL"] == [
            ("Strength", 1, 5, "●○○○○"),
            ("Dexterity", 2, 5, "●●○○○"),
            ("Stamina", 3, 5, "●●●○○"),
        ]

        assert trait_values["SKILLS"] == [("Test_Trait", 2, 5, "●●○○○")]

    @staticmethod
    def test_character_custom_traits() -> None:
        """Test the custom_traits method of the Character class.

        GIVEN: A Character object with custom traits.
        WHEN: The custom_traits method is called.
        THEN: All custom traits should be returned as expected.
        """
        # GIVEN: A Character object with custom traits
        # (Assuming that the Character with id=1 has the custom traits as described in the test)

        # WHEN: The custom_traits method is called
        custom_traits = Character.get_by_id(1).custom_traits

        # THEN: All custom traits should be returned as expected
        assert custom_traits is not None, "Custom traits should not be None"
        assert len(custom_traits) == 1, "There should be exactly one custom trait"

        first_trait = custom_traits[0]
        assert (
            first_trait.name == "Test_Trait"
        ), "The name of the first custom trait should be 'Test_Trait'"

    @staticmethod
    def test_character_get_trait_value(mock_ctx):
        """Test character.get_trait_value() method.

        This test verifies that the method correctly returns the value of a given trait or custom trait.
        It also checks that the method returns 0 for a trait that does not exist for the character.
        """
        # GIVEN a character with a custom trait and a trait value
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=mock_ctx.author.id,
            clan=1,
        )
        custom_trait = CustomTrait.create(
            name="test_trait",
            description="test_description",
            category=1,
            value=4,
            max_value=5,
            character=character,
        )
        trait = Trait.get_by_id(1)
        TraitValue.create(character=character, trait=trait, value=2)

        # WHEN the get_trait_value method is called with a CustomTrait
        # THEN check the trait value is returned correctly
        assert character.get_trait_value(custom_trait) == 4, "Custom trait value should be 4"

        # WHEN the get_trait_value method is called with a Trait
        # THEN check the trait value is returned correctly
        assert character.get_trait_value(trait) == 2, "Trait value should be 2"

        # WHEN the get_trait_value method is called with a TraitValue that does not exist
        # THEN return 0 for the value
        non_existent_trait_value = TraitValue(trait=Trait.get_by_id(2))
        assert (
            character.get_trait_value(non_existent_trait_value) == 0
        ), "Non-existent trait value should be 0"

    @staticmethod
    def test_set_custom_trait_value(mock_ctx):
        """Test setting a value for a custom trait using character.set_trait_value()."""
        # GIVEN a character with a custom trait
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=mock_ctx.author.id,
            clan=1,
        )
        custom_trait = CustomTrait.create(
            name="test_trait",
            description="test_description",
            category=1,
            value=0,
            max_value=5,
            character=character,
        )

        # WHEN the set_trait_value method is called with a CustomTrait
        character.set_trait_value(custom_trait, 3)

        # THEN check the trait value is updated correctly
        assert custom_trait.value == 3

    @staticmethod
    def test_create_new_trait_value(mock_ctx):
        """Test creating a new trait value using character.set_trait_value()."""
        # GIVEN a character without a standard trait value
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=mock_ctx.author.id,
            clan=1,
        )
        trait = Trait.get_by_id(1)

        # WHEN the set_trait_value method is called with a Trait
        character.set_trait_value(trait, 3)

        # THEN check the trait value is created correctly
        assert (
            TraitValue.select()
            .where((TraitValue.trait == trait) & (TraitValue.character == character))
            .get()
            .value
            == 3
        )

    @staticmethod
    def test_update_existing_trait_value(mock_ctx):
        """Test updating an existing trait value using character.set_trait_value()."""
        # GIVEN a character with an existing standard trait value
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=mock_ctx.author.id,
            clan=1,
        )
        trait = Trait.get_by_id(1)
        TraitValue.create(character=character, trait=trait, value=3)

        # WHEN the set_trait_value method is called with a Trait
        character.set_trait_value(trait, 1)

        # THEN check the trait value is updated correctly
        assert (
            TraitValue.select()
            .where((TraitValue.trait == trait) & (TraitValue.character == character))
            .get()
            .value
            == 1
        )

    def test_kill_character(self):
        """Test character.kill()."""
        self._clear_test_data()

        # GIVEN a character
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "storyteller_character": True,
                "is_alive": True,
                "is_active": True,
            },
            char_class=1,
            guild=1,
            created_by=1,
            owner_by=1,
            clan=1,
        )

        # WHEN the kill method is called
        character.kill()

        # THEN check the character is killed correctly
        assert not character.is_alive
        assert not character.is_active

    @staticmethod
    def test_character_traits_dict():
        """Test character.traits_dict.

        Given a character with traits
        When character.traits_dict is called
        Then all traits associated with that character are returned as a dictionary
        """
        returned = Character.get_by_id(1).traits_dict

        assert returned == {
            "PHYSICAL": [Trait.get_by_id(1), Trait.get_by_id(2), Trait.get_by_id(3)],
            "SKILLS": [CustomTrait.get_by_id(1)],
        }

    @staticmethod
    def test_character_traits_list():
        """Test character.traits_list.

        Given a character with traits
        When character.all_traits_list is called as a flat list
        Then all traits associated with that character are returned as a list
        """
        returned = Character.get_by_id(1).traits_list
        assert returned == [
            Trait.get_by_id(2),
            Trait.get_by_id(3),
            Trait.get_by_id(1),
            CustomTrait.get_by_id(1),
        ]


@pytest.mark.usefixtures("mock_db")
class TestCharacterService:
    """Test the character service."""

    char_svc = CharacterService()

    @staticmethod
    def _clear_test_data() -> None:
        """Clear all test data from the database."""
        for character in Character.select():
            if character.id == 1:  # Always keep the first character created in conftest.py
                continue
            character.delete_instance(recursive=True, delete_nullable=True)

    @staticmethod
    def _mock_fetch_all_class_traits(
        char_class: CharClassType = CharClassType.MORTAL,
    ) -> list[Trait]:
        """Mock the fetch_all_class_traits method of the TraitService class."""
        traits = (
            Trait.select()
            .join(TraitClass)
            .join(CharacterClass)
            .where(CharacterClass.name == char_class.name)
        )

        return sorted(traits, key=lambda x: TraitCategories[x.category.name].value["order"])

    def test_custom_section_update_or_add(self, mock_ctx):
        """Test if custom_section_update_or_add() correctly adds or updates a custom section.

        This test covers two scenarios:
        1. Adding a new custom section to an empty list of custom sections.
        2. Updating an existing custom section.

        Args:
            mock_ctx (Mock): Mocked context for the service function call.
        """
        # GIVEN a character object with no custom sections
        character = Character.create(
            data={
                "first_name": "add_custom_section",
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=1,
            created_by=1,
            clan=1,
        )
        assert character.custom_sections == [], "Initial custom sections should be empty"

        # WHEN the custom_section_update_or_add method is called for the first time
        result1 = self.char_svc.custom_section_update_or_add(
            mock_ctx, character, "new", "new description"
        )

        # THEN check that the custom section is added correctly
        assert character.custom_sections == IsList(length=1), "One custom section should be added"
        assert result1.title == "new", "The title should match the initial input"
        assert (
            result1.description == "new description"
        ), "The description should match the initial input"

        # WHEN the custom_section_update_or_add method is called a second time with different details
        result2 = self.char_svc.custom_section_update_or_add(
            mock_ctx, character, "new2", "new description2"
        )

        # THEN check that the existing custom section is updated correctly
        assert character.custom_sections == IsList(
            length=1
        ), "Should still be only one custom section after update"
        assert result2.title == "new2", "The title should be updated to 'new2'"
        assert (
            result2.description == "new description2"
        ), "The description should be updated to 'new description2'"

    def test_fetch_all_player_characters(self, mocker, mock_member, mock_member2):
        """Test fetch_all_player_characters()."""
        # GIVEN characters for a guild

        local_mock_guild = mocker.MagicMock()
        local_mock_guild.id = randint(1000, 99999)
        local_mock_guild.__class__ = discord.Guild
        local_mock_ctx = mocker.MagicMock()
        local_mock_ctx.guild = local_mock_guild
        local_mock_ctx.__class__ = discord.ApplicationContext

        character1 = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character1",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=mock_member.id,
            owned_by=mock_member.id,
            clan=1,
        )
        character2 = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character2",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=mock_member.id,
            owned_by=mock_member.id,
            clan=1,
        )
        # Created by a second user
        character3 = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character3",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=mock_member2.id,
            owned_by=mock_member2.id,
            clan=1,
        )
        # not a player character
        Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character4",
                "storyteller_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=mock_member.id,
            owned_by=mock_member.id,
            clan=1,
        )
        # not in the guild
        Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character5",
                "player_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id + 5,
            created_by=mock_member.id,
            owned_by=mock_member.id,
            clan=1,
        )

        # WHEN the fetch_all_player_characters method is called
        result = self.char_svc.fetch_all_player_characters(local_mock_ctx)

        # THEN check the method returns the correct characters database and updates the default values
        assert result == [character1, character2, character3]
        assert result[0].data["is_alive"]  # Check default value

        # WHEN the fetch_all_player_characters method is called with a user
        result = self.char_svc.fetch_all_player_characters(local_mock_ctx, owned_by=mock_member)
        assert result == [character1, character2]

    def test_fetch_all_storyteller_characters(self, mocker):
        """Test fetch_all_storyteller_characters()."""
        # GIVEN characters for a guild
        local_mock_guild = mocker.MagicMock()
        local_mock_guild.id = randint(1000, 99999)
        local_mock_guild.__class__ = discord.Guild
        local_mock_ctx = mocker.MagicMock()
        local_mock_ctx.guild = local_mock_guild
        local_mock_ctx.__class__ = discord.ApplicationContext

        character1 = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "storyteller_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=1,
            clan=1,
        )
        character2 = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "storyteller_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=1,
            clan=1,
        )
        # not a storyteller character
        Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "player_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id,
            created_by=1,
            clan=1,
        )
        # not in the guild
        Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "storyteller_character": True,
            },
            char_class=1,
            guild=local_mock_ctx.guild.id + 5,
            created_by=1,
            clan=1,
        )

        # WHEN the fetch_all_storyteller_characters method is called
        result = self.char_svc.fetch_all_storyteller_characters(local_mock_ctx)

        # THEN check the method returns the correct characters database and updates the default values
        assert result == [character1, character2]
        assert result[0].data["is_alive"]  # Check default value

    @pytest.mark.asyncio()
    async def test_update_or_add_one(self, mock_ctx):
        """Test update_character()."""
        # GIVEN a character object
        user, _ = GuildUser.get_or_create(user=mock_ctx.author.id, guild=mock_ctx.guild.id)

        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": False,
                "player_character": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user,
            clan=1,
        )

        # WHEN the update_or_add method is called
        updates = {"first_name": "updated", "last_name": "updated", "nickname": "updated"}
        result = await self.char_svc.update_or_add(mock_ctx, character=character, data=updates)

        # THEN check the character is updated correctly
        assert result.data == IsPartialDict(
            first_name="updated",
            last_name="updated",
            nickname="updated",
            storyteller_character=False,
        )

    @pytest.mark.asyncio()
    async def test_update_or_add_two(self, mock_ctx):
        """Test update_or_add()."""
        user, _ = GuildUser.get_or_create(user=mock_ctx.author.id, guild=mock_ctx.guild.id)

        # GIVEN a storyteller character object
        character = Character.create(
            data={
                "first_name": str(uuid4()).split("-")[0],
                "last_name": "character",
                "nickname": "testy",
                "storyteller_character": True,
                "player_character": False,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user,
            clan=1,
        )

        # WHEN the update_or_add method is called
        updates = {"first_name": "updated", "last_name": "updated", "nickname": "updated"}
        result = await self.char_svc.update_or_add(
            mock_ctx, character=character, data=updates, clan=2
        )

        # THEN check the character is updated correctly
        assert result.data == IsPartialDict(
            first_name="updated",
            last_name="updated",
            nickname="updated",
            storyteller_character=True,
        )
        assert result.clan == VampireClan.get_by_id(1)

    @pytest.mark.asyncio()
    async def test_update_or_add_three(self, mock_ctx):
        """Test update_or_add()."""
        # Mock the call to fetch_user
        user, _ = GuildUser.get_or_create(user=mock_ctx.author.id, guild=mock_ctx.guild.id)
        mock_ctx.bot.user_svc.fetch_user = AsyncMock(return_value=user)

        # GIVEN a character that is not created
        name = str(uuid4()).split("-")[0]
        data = {
            "first_name": name,
            "new_key": "new_value",
        }

        # WHEN the update_or_add method is called
        result = await self.char_svc.update_or_add(
            mock_ctx, data=data, char_class=CharClassType.VAMPIRE, clan=VampireClanType.BRUJAH
        )

        # THEN check the character is created correctly with default values
        assert result.data == IsPartialDict(
            first_name=name, storyteller_character=False, new_key="new_value", is_alive=True
        )
        assert not result.data["last_name"]
        assert not result.data["nickname"]

    @pytest.mark.asyncio()
    async def test_rng_creator_full_random(self, mock_ctx, mocker):
        """Test rng_creator() with full random."""
        self._clear_test_data()

        mock_ctx.bot.user_svc.fetch_user = AsyncMock(return_value=GuildUser.get_by_id(1))

        # Mock Random Name
        async_mock = AsyncMock(return_value=[("John", "Doe")])
        mocker.patch("valentina.models.characters.fetch_random_name", side_effect=async_mock)

        # Mock all_class_traits
        all_class_traits = self._mock_fetch_all_class_traits()
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        result = await self.char_svc.rng_creator(mock_ctx, player_character=True)

        assert result.char_class.name in CharClassType.__members__
        assert result.data["first_name"] == "John"
        assert result.data["last_name"] == "Doe"
        assert not result.data["nickname"]
        assert result.data["player_character"]
        assert result.data["storyteller_character"] is False
        assert result.data["chargen_character"] is False
        assert result.data["developer_character"] is False

    @pytest.mark.asyncio()
    async def test_rng_creator_with_options(self, mock_ctx, mocker):
        """Test rng_creator() with full random."""
        self._clear_test_data()

        mock_ctx.bot.user_svc.fetch_user = AsyncMock(return_value=GuildUser.get_by_id(1))

        # Mock Random Name
        async_mock = AsyncMock(return_value=[("John", "Doe")])
        mocker.patch("valentina.models.characters.fetch_random_name", side_effect=async_mock)

        # Mock all_class_traits
        all_class_traits = self._mock_fetch_all_class_traits()
        mock_ctx.bot.trait_svc.fetch_all_class_traits = MagicMock(return_value=all_class_traits)

        result = await self.char_svc.rng_creator(
            mock_ctx,
            storyteller_character=True,
            nickname_is_class=True,
            char_class=CharClassType.VAMPIRE,
        )

        assert result.char_class.name == "VAMPIRE"
        assert result.data["first_name"] == "John"
        assert result.data["last_name"] == "Doe"
        assert result.data["nickname"] == "Vampire"
        assert result.data["player_character"] is False
        assert result.data["storyteller_character"]
        assert result.data["chargen_character"] is False
        assert result.data["developer_character"] is False
        assert result.clan.name in VampireClanType.__members__
