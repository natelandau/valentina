# type: ignore
"""Test the mongodb character model."""

import pytest
from rich import print

from tests.factories import *
from valentina.constants import CharacterConcept, CharClass, HunterCreed, TraitCategory, VampireClan
from valentina.models import Character, CharacterTrait
from valentina.utils import errors


async def test_create_new(character_factory):
    """Test creating a new character."""
    # GIVEN a character
    character = character_factory.build(
        name_first="John",
        name_last="Doe",
        name_nick=None,
        char_class_name="MORTAL",
        concept_name="SOLDIER",
        clan_name="BRUJAH",
        creed_name="AVENGER",
    )

    # THEN the computed properties are correct
    assert character.name == "John Doe"
    assert character.full_name == "John Doe"
    assert character.char_class == CharClass.MORTAL
    assert character.concept == CharacterConcept.SOLDIER
    assert character.clan == VampireClan.BRUJAH
    assert character.creed == HunterCreed.AVENGER


@pytest.mark.no_db
async def test_custom_enum_names(character_factory):
    """Test creating a character with invalid enum names."""
    # GIVEN a character
    character = character_factory.build(
        clan_name="not a clan",
        creed_name="not a creed",
        char_class_name="not a mortal",
        concept_name="not a concept",
    )

    # THEN don't return enum values when calling enum properties
    assert character.concept is None
    assert character.clan is None
    assert character.creed is None
    with pytest.raises(errors.NoCharacterClassError):
        assert character.char_class


@pytest.mark.no_db
async def test_full_name(character_factory):
    """Test the full_name computed property."""
    # GIVEN a character
    character = character_factory.build(
        name_first="John",
        name_last="Doe",
        name_nick=None,
    )

    # WHEN the full_name property is accessed with no nickname
    # THEN the correct value is returned
    assert character.full_name == "John Doe"

    # WHEN the full_name property is accessed with a nickname
    character.name_nick = "JD"

    # THEN the correct value is returned
    assert character.full_name == "John 'JD' Doe"


@pytest.mark.drop_db
async def test_add_custom_trait(character_factory):
    """Test the add_trait method."""
    # GIVEN a character
    character = character_factory.build()
    await character.insert()

    # WHEN adding a trait
    trait = await character.add_trait(TraitCategory.BACKGROUNDS, "Something", 3, 5)

    # THEN the trait is added to the character
    assert len(character.traits) == 1
    assert character.traits[0] == trait

    # AND the trait is saved to the database
    all_traits = await CharacterTrait.find_all().to_list()
    assert len(all_traits) == 1
    assert all_traits[0].name == "Something"
    assert all_traits[0].value == 3
    assert all_traits[0].max_value == 5
    assert all_traits[0].category_name == TraitCategory.BACKGROUNDS.name
    assert all_traits[0].character == str(character.id)
    assert all_traits[0].is_custom


@pytest.mark.drop_db
async def test_add_trait(character_factory):
    """Test the add_trait method."""
    # GIVEN a character
    character = character_factory.build()
    await character.insert()

    # WHEN adding a trait that exists in TraitCategory enum
    trait = await character.add_trait(TraitCategory.PHYSICAL, "Strength", 2, 10)

    # THEN the trait is added to the character
    assert len(character.traits) == 1
    assert character.traits[0] == trait

    # AND the trait is saved to the database
    # With the max_value reset to the enum defaults
    all_traits = await CharacterTrait.find_all().to_list()
    assert len(all_traits) == 1
    assert all_traits[0].name == "Strength"
    assert all_traits[0].value == 2
    assert all_traits[0].max_value == 5
    assert all_traits[0].category_name == TraitCategory.PHYSICAL.name
    assert all_traits[0].character == str(character.id)
    assert not all_traits[0].is_custom


@pytest.mark.no_db
async def test_add_trait_already_exists(character_factory, trait_factory):
    """Test the add_trait method."""
    # GIVEN a character with an existing trait
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=10
    )
    character = character_factory.build(traits=[trait])

    # WHEN adding a trait that already exists on the character
    # THEN a TraitExistsError is raised
    with pytest.raises(errors.TraitExistsError):
        await character.add_trait(TraitCategory.PHYSICAL, "Strength", 2, 10)


@pytest.mark.drop_db
async def test_add_trait_no_values(character_factory):
    """Test the add_trait method."""
    # GIVEN a character
    character = character_factory.build()
    await character.insert()

    # WHEN adding a trait without required values
    # THEN a ValueError is raised
    with pytest.raises(ValueError, match="required to create a new trait"):
        await character.add_trait(name="Strength", value=1)
    with pytest.raises(ValueError, match="required to create a new trait"):
        await character.add_trait(name="Strength", category="PHYSICAL")
    with pytest.raises(ValueError, match="required to create a new trait"):
        await character.add_trait(value=1, category="PHYSICAL")


@pytest.mark.drop_db
async def test_add_trait_charactertrait(character_factory, trait_factory) -> None:
    """Test the add_trait method when providing a CharacterTrait."""
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=10
    )
    await trait.insert()
    character = character_factory.build()
    await character.insert()

    # WHEN adding a CharacterTrait object to the character
    new_trait = await character.add_trait(character_trait=trait)

    # THEN the trait is added to the character
    char = await Character.get(character.id, fetch_links=True)
    assert len(char.traits) == 1
    assert char.traits[0] == new_trait
    assert char.traits[0].character == str(char.id)

    # When adding a trait that already exists on the character
    # assert that no errors are raised
    new_trait = await char.add_trait(character_trait=trait)
    c = await Character.get(character.id, fetch_links=True)
    assert len(c.traits) == 1
    assert c.traits[0] == new_trait
    assert c.traits[0].character == str(c.id)


@pytest.mark.no_db
async def test_fetch_trait_by_name(character_factory, trait_factory):
    """Test the fetch_trait_by_name method."""
    # GIVEN a character with a traits
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=5
    )
    character = character_factory.build(traits=[trait])

    # WHEN fetching a trait by name
    trait = await character.fetch_trait_by_name("Strength")

    # THEN the correct trait is returned
    assert trait.name == "Strength"
    assert trait.max_value == 5

    # WHEN fetching a trait by name that doesn't exist
    # THEN None is returned
    assert await character.fetch_trait_by_name("Not a trait") is None
