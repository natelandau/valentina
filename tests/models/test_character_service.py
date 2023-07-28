# type: ignore
"""Test the CharacterService class."""

import pytest

from valentina.models.database import Character, CustomSection, CustomTrait, Trait, TraitCategory
from valentina.models.database_services import CharacterService
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    NoClaimError,
    TraitNotFoundError,
)


@pytest.mark.usefixtures("mock_db")
class TestCharacterService:
    """Test the character service."""

    char_svc = CharacterService()

    def test_add_claim_one(self):
        """Test add_claim().

        Given a guild, character, and user
        When a claim is added
        Then the claim is added to claim cache
        """
        assert self.char_svc.claims == {}
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        assert self.char_svc.claims == {"1_1": "1_1"}

    def test_add_claim_two(self):
        """Test add_claim().

        Given a guild, character, and user
        When a user has a claim and claims another character
        Then the new claim replaces the old claim
        """
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        self.char_svc.add_claim(guild_id=1, char_id=2, user_id=1)
        assert self.char_svc.claims == {"1_1": "1_2"}

    def test_add_claim_three(self):
        """Test add_claim().

        Given a guild, character, and user
        When another has the requested character claimed
        Then CharacterClaimedError is raised
        """
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        with pytest.raises(CharacterClaimedError):
            self.char_svc.add_claim(guild_id=1, char_id=1, user_id=22)

    def test_add_custom_section_one(self):
        """Test add_custom_section().

        Given a ctx object and a character
        When a custom section is added
        Then the custom section is added to the database
        """
        character = Character.get_by_id(1)

        self.char_svc.add_custom_section(character, "new", "new description")
        section = CustomSection.get(CustomSection.id == 2)
        assert section.title == "new"
        section.delete_instance()

    def test_add_trait_one(self):
        """Test add_trait().

        Given a ctx object and a character
        When a trait is added
        Then the trait is added to the database and cache
        """
        self.char_svc.add_trait(
            character=Character.get_by_id(1),
            name="test_trait2",
            value=2,
            category=TraitCategory.get(name="Skills"),
            description="test_description",
        )

        # Added to database
        trait = CustomTrait.get(CustomTrait.id == 2)
        assert trait.name == "Test_Trait2"

    @pytest.mark.parametrize(
        (
            "id",
            "expected",
        ),
        [(1, True), (789, False)],
    )
    def test_is_cached_char(self, id, expected) -> bool:
        """Test is_cached_char().

        Given a character id
        When is_cached_char is called
        Then the expected result is returned
        """
        self.char_svc.fetch_all_characters(1)
        assert self.char_svc.is_cached_char(1, id) == expected

    def test_fetch_all_characters_one(self):
        """Test fetch_all_characters().

        Given a guild
        When fetch_all_characters is called
        Then all characters associated with that guild are returned
        """
        self.char_svc.purge_cache()
        assert len(self.char_svc.characters) == 0
        characters = self.char_svc.fetch_all_characters(1)
        assert len(self.char_svc.characters) == 2
        assert len(characters) == 2

    def test_character_traits_dict(self):
        """Test character.traits_dict.

        Given a character with traits
        When character.traits_dict is called
        Then all traits associated with that character are returned as a dictionary
        """
        returned = Character.get_by_id(1).traits_dict

        assert returned == {
            "Physical": [Trait.get_by_id(1), Trait.get_by_id(2), Trait.get_by_id(3)],
            "Skills": [CustomTrait.get_by_id(1), CustomTrait.get_by_id(2)],
        }

    def test_character_traits_list(self):
        """Test character.traits_list).

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
            CustomTrait.get_by_id(2),
        ]

    def test_character_all_trait_values(self):
        """Test character.all_trait_values.

        Given a character with traits
        When character.all_trait_values is called
        Then all trait values are returned as a dictionary containing the appropriate tuple values
        """
        returned = Character.get_by_id(1).all_trait_values

        assert returned["Physical"] == [
            ("Strength", 1, 5, "●○○○○"),
            ("Dexterity", 2, 5, "●●○○○"),
            ("Stamina", 3, 5, "●●●○○"),
        ]
        assert returned["Skills"] == [
            ("Test_Trait", 2, 5, "●●○○○"),
            ("Test_Trait2", 2, 5, "●●○○○"),
        ]

    def test_char_custom_sections(self):
        """Test character.custom_sections.

        Given a character with custom sections
        When character.custom_sections is called
        Then all custom sections are returned
        """
        returned = Character.get_by_id(1).custom_sections
        assert len(returned) == 1
        assert returned[0].title == "test_section"

    def test_character_custom_traits(self):
        """Test character.custom_traits.

        Given a character with custom traits
        When character.custom_traits is called
        Then all custom traits are returned
        """
        returned = Character.get_by_id(1).custom_traits
        assert len(returned) == 2
        assert returned[0].name == "Test_Trait"
        assert returned[1].name == "Test_Trait2"

    def test_fetch_claim(self, ctx_existing):
        """Test fetch_claim().

        Given a guild, character, and user
        When fetch_claim is called
        Then the claimed character is returned or NoClaimError is raised
        """
        # Raise NoClaimError if no claim exists
        self.char_svc.claims = {}
        with pytest.raises(NoClaimError):
            self.char_svc.fetch_claim(ctx_existing)

        # Return the claim if it exists in cache
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        returned = self.char_svc.fetch_claim(ctx_existing)
        assert returned.id == 1
        assert returned.name == "Test (Testy) Character"

        # Return the claim if it exists in database
        self.char_svc.purge_cache()
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        returned = self.char_svc.fetch_claim(ctx_existing)
        assert returned.id == 1
        assert returned.name == "Test (Testy) Character"

    @pytest.mark.parametrize(
        ("char_id", "expected"),
        [
            (1, 1),
            (2, None),
            (3, None),
        ],
    )
    def test_fetch_user_of_character(self, char_id, expected):
        """Test fetch_user_of_character().

        Given a character id and a guild id
        When fetch_user_of_character is called
        Then fetch the user who claimed the character, if any
        """
        self.char_svc.purge_cache()
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        assert self.char_svc.fetch_user_of_character(1, char_id) == expected

    def test_remove_claim(self, ctx_existing):
        """Test remove_claim().

        Given a ctx object
        When remove_claim is called
        Then the character is unclaimed
        """
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        assert self.char_svc.remove_claim(ctx_existing) is True
        assert self.char_svc.remove_claim(ctx_existing) is False

    def test_user_has_claim(self, ctx_existing):
        """Test user_has_claim().

        Given a ctx object
        When user_has_claim is called
        Then True is returned if the user has a claim and False otherwise
        """
        self.char_svc.remove_claim(ctx_existing)
        assert self.char_svc.user_has_claim(ctx_existing) is False
        self.char_svc.add_claim(guild_id=1, char_id=1, user_id=1)
        assert self.char_svc.user_has_claim(ctx_existing) is True

    def test_update_character(self, ctx_existing):
        """Test update_character().

        Given a character id and a dict of updates
        When update_character is called
        Then the character is updatedin the database and purged from the cache
        """
        character = Character.get_by_id(1)
        assert character.experience == 0

        self.char_svc.update_character(ctx_existing, 1, **{"experience": 5})
        character = Character.get_by_id(1)
        assert character.experience == 5
        assert "1_1" not in self.char_svc.characters

        with pytest.raises(CharacterNotFoundError):
            self.char_svc.update_character(ctx_existing, 12345678, **{"experience": 5})

    def test_update_trait_value_by_name(self, ctx_existing):
        """Test update_trait_value_by_name().

        Given a character id, trait name, and new value
        When update_trait_value_by_name is called
        Then the trait value is updated in the database and purged from the cache
        """
        # TODO: Test for updating a non-custom trait

        character = Character.get_by_id(1)
        custom = CustomTrait.get_by_id(1)
        assert custom.value == 2
        name = custom.name
        self.char_svc.update_trait_value_by_name(ctx_existing, character, name, 5)
        custom = CustomTrait.get_by_id(1)
        assert custom.value == 5

        with pytest.raises(TraitNotFoundError):
            self.char_svc.update_trait_value_by_name(ctx_existing, character, "exception", 5)
