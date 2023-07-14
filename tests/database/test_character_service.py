# type: ignore
"""Test the CharacterService class."""

import pytest

from valentina.models.database import (
    Character,
    CustomSection,
    CustomTrait,
    Trait,
)
from valentina.models.database_services import CharacterService
from valentina.utils.errors import (
    CharacterClaimedError,
    CharacterNotFoundError,
    NoClaimError,
    SectionNotFoundError,
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

    def test_add_custom_section_one(self, ctx_existing):
        """Test add_custom_section().

        Given a ctx object and a character
        When a custom section is added
        Then the custom section is added to the database
        """
        character = Character.get(Character.id == 1)
        self.char_svc.fetch_char_custom_sections(ctx=ctx_existing, character=character)
        assert "1_1" in self.char_svc.custom_sections

        self.char_svc.add_custom_section(ctx_existing, character, "new", "new description")
        assert "1_1" not in self.char_svc.custom_sections
        section = CustomSection.get(CustomSection.id == 2)
        assert section.title == "new"
        section.delete_instance()

    def test_add_trait_one(self, ctx_existing, existing_character):
        """Test add_trait().

        Given a ctx object and a character
        When a trait is added
        Then the trait is added to the database and cache
        """
        assert self.char_svc.custom_traits == {}
        self.char_svc.add_trait(
            ctx=ctx_existing,
            character=existing_character,
            name="test_trait2",
            value=2,
            category="test_category",
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
        assert self.char_svc.fetch_by_id(1, 1)
        assert self.char_svc.is_cached_char(1, id) == expected

    def test_fetch_all_characters_one(self):
        """Test fetch_all_characters().

        Given a guild
        When fetch_all_characters is called
        Then all characters associated with that guild are returned
        """
        self.char_svc.purge_cache()
        assert len(self.char_svc.characters) == 0
        assert self.char_svc.fetch_by_id(1, 1)
        assert len(self.char_svc.characters) == 1
        characters = self.char_svc.fetch_all_characters(1)
        assert len(self.char_svc.characters) == 2
        assert len(characters) == 2

    def test_fetch_all_character_traits_one(self, existing_character):
        """Test fetch_all_character_traits().

        Given a character with traits
        When fetch_all_character_traits is called
        Then all traits associated with that character are returned as a dictionary
        """
        returned = self.char_svc.fetch_all_character_traits(existing_character)

        assert returned == {
            "Physical": ["Strength", "Dexterity", "Stamina"],
            "Test_Category": ["Test_Trait", "Test_Trait2"],
        }

    def test_fetch_all_character_traits_two(self, existing_character):
        """Test fetch_all_character_traits().

        Given a character with traits
        When fetch_all_character_traits is called as a flat list
        Then all traits associated with that character are returned as a list
        """
        returned = self.char_svc.fetch_all_character_traits(existing_character, flat_list=True)
        assert returned == ["Dexterity", "Stamina", "Strength", "Test_Trait", "Test_Trait2"]

    def test_fetch_all_character_trait_values(self, ctx_existing):
        """Test fetch_all_character_trait_values().

        Given a character with traits
        When fetch_all_character_trait_values is called
        Then all trait values are returned as a dictionary containing the appropriate tuple values
        """
        character = Character.get_by_id(1)
        returned = self.char_svc.fetch_all_character_trait_values(ctx_existing, character)

        assert returned["Physical"] == [
            ("Strength", 1, 5, "●○○○○"),
            ("Dexterity", 2, 5, "●●○○○"),
            ("Stamina", 3, 5, "●●●○○"),
        ]
        assert returned["Test_Category"] == [
            ("Test_Trait", 2, 5, "●●○○○"),
            ("Test_Trait2", 2, 5, "●●○○○"),
        ]

    def test_fetch_char_custom_sections(self, ctx_existing, existing_character):
        """Test fetch_char_custom_sections().

        Given a character with custom sections
        When fetch_char_custom_sections is called
        Then all custom sections are returned as a list
        """
        returned = self.char_svc.fetch_char_custom_sections(ctx_existing, existing_character)
        assert len(returned) == 1
        assert returned[0].title == "test_section"

    def test_fetch_custom_section(self, ctx_existing):
        """Test fetch_custom_section().

        Given a section title and a character
        When fetch_custom_section is called
        Then the section is returned or SectionNotFoundError is raised
        """
        character = Character.get(Character.id == 1)
        returned = self.char_svc.fetch_custom_section(ctx_existing, character, "test_section")
        assert returned.title == "test_section"

        with pytest.raises(SectionNotFoundError):
            self.char_svc.fetch_custom_section(ctx_existing, character, "exception")

    def test_fetch_char_custom_traits(self, ctx_existing, existing_character):
        """Test fetch_char_custom_traits().

        Given a character with custom traits
        When fetch_char_custom_traits is called
        Then all custom traits are returned in a list
        """
        self.char_svc.custom_traits = {}
        returned = self.char_svc.fetch_char_custom_traits(ctx_existing, existing_character)
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
        ("trait", "expected"),
        [
            ("Test_Trait", 2),
            ("strength", 1),
            ("DEXTERITY", 2),
            ("exception", 2),
        ],
    )
    def test_fetch_trait_value(self, ctx_existing, trait, expected):
        """Test fetch_trait_value().

        Given a trait name
        When fetch_trait_value is called
        Then the trait value is returned
        """
        character = Character.get_by_id(1)

        if trait == "exception":
            with pytest.raises(TraitNotFoundError):
                self.char_svc.fetch_trait_value(ctx_existing, character, trait)
        else:
            assert self.char_svc.fetch_trait_value(ctx_existing, character, trait) == expected

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
        self.char_svc.fetch_by_id(1, 1)
        assert "1_1" in self.char_svc.characters

        self.char_svc.update_character(ctx_existing, 1, **{"experience": 5})
        character = Character.get_by_id(1)
        assert character.experience == 5
        assert "1_1" not in self.char_svc.characters

        with pytest.raises(CharacterNotFoundError):
            self.char_svc.update_character(ctx_existing, 12345678, **{"experience": 5})

    def test_update_custom_section(self, ctx_existing):
        """Test update_custom_section().

        Given a character id, section name, and new value
        When update_custom_section is called
        Then the section value is updated in the database and purged from the cache
        """
        character = Character.get_by_id(1)
        self.char_svc.fetch_char_custom_sections(ctx_existing, character)
        assert "1_1" in self.char_svc.custom_sections

        properties = {"title": "a new title", "description": "a new description"}
        self.char_svc.update_custom_section(ctx_existing, 1, **properties)

        assert "1_1" not in self.char_svc.custom_sections
        section = CustomSection.get_by_id(1)
        assert section.title == "a new title"
        assert section.description == "a new description"

        with pytest.raises(SectionNotFoundError):
            self.char_svc.update_custom_section(ctx_existing, 12345678, **properties)

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
