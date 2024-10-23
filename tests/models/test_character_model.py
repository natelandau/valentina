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
async def test_add_trait_already_exists(character_factory, trait_factory):
    """Test the add_trait method."""
    # GIVEN a character with an existing trait
    trait = trait_factory.build(
        category_name=TraitCategory.PHYSICAL.name, name="Strength", value=2, max_value=10
    )
    await trait.save()
    character = character_factory.build(traits=[trait])
    await character.save()

    # When the same trait is added a second time, the existing trait is returned
    existing_trait = await CharacterTrait.get(trait.id)
    assert await character.add_trait(existing_trait) == trait

    # WHEN adding a new trait with the same name and category
    # THEN a TraitExistsError is raised
    with pytest.raises(errors.TraitExistsError):
        await character.add_trait(
            CharacterTrait(
                name="Strength",
                category_name="PHYSICAL",
                value=4,
                max_value=5,
                character=str(character.id),
            )
        )


@pytest.mark.drop_db
async def test_add_trait(character_factory) -> None:
    """Test the add_trait method when providing a CharacterTrait."""
    trait = CharacterTrait(
        category_name=TraitCategory.PHYSICAL.name,
        name="Strength",
        value=2,
        max_value=10,
        character="something",
    )
    await trait.insert()
    character = character_factory.build()
    await character.insert()

    # WHEN adding a CharacterTrait object to the character
    new_trait = await character.add_trait(trait)

    # THEN the trait is added to the character and the database
    char = await Character.get(character.id, fetch_links=True)
    assert len(char.traits) == 1
    assert char.traits[0] == new_trait
    assert char.traits[0].character == str(char.id)
    assert await CharacterTrait.get(new_trait.id) == new_trait


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
