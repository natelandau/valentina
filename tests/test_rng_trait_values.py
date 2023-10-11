# type: ignore
"""Test the RNGTraitValue class."""

from unittest.mock import MagicMock

import pytest

from valentina.constants import CharClassType, CharConcept, RNGCharLevel, TraitCategories
from valentina.models.characters import CharacterTraitRandomizer
from valentina.models.db_tables import Character, CharacterClass, VampireClan
from valentina.models.traits import TraitService


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
            TraitCategories.TALENTS,
            TraitCategories.SKILLS,
            TraitCategories.KNOWLEDGES,
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
                TraitCategories.PHYSICAL,
                TraitCategories.SOCIAL,
                TraitCategories.MENTAL,
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
        ("char_class", "clan", "level", "clan_disciplines", "num_disciplines"),
        [
            ("VAMPIRE", "BRUJAH", "NEW", ["Celerity", "Potence", "Presence"], 3),
            ("MORTAL", None, "NEW", [], 0),
            ("VAMPIRE", "GIOVANNI", "INTERMEDIATE", ["Dominate", "Necromancy", "Potence"], 4),
            ("VAMPIRE", "MALKAVIAN", "ADVANCED", ["Auspex", "Dominate", "Obfuscate"], 5),
            ("VAMPIRE", "VENTRUE", "ELITE", ["Dominate", "Fortitude", "Presence"], 6),
        ],
    )
    def test__set_disciplines(
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
