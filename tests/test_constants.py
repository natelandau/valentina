# type: ignore
"""Test the constants module."""

import pytest

from valentina.constants import (
    CharacterConcept,
    CharClass,
    CharClassValue,
    HunterCreed,
    TraitCategory,
    VampireClan,
)


@pytest.mark.no_db
def test_random_vampire_clan() -> None:
    """Test the random_vampire_clan function."""
    result = VampireClan.random_member()
    assert result.name in VampireClan.__members__


@pytest.mark.no_db
def test_character_concept_random_member():
    """Test the CharacterConcept enum."""
    for _ in range(50):
        random = CharacterConcept.random_member()
        assert CharacterConcept[random.name] == random


@pytest.mark.no_db
def test_concept_get_member_by_value():
    """Test the CharacterConcept enum get_member_by_value method."""
    # GIVEN a CharacterConcept member
    value_map: dict[int, CharClass] = {
        1: CharacterConcept.BERSERKER,
        11: CharacterConcept.PERFORMER,
        25: CharacterConcept.HEALER,
        31: CharacterConcept.SHAMAN,
        39: CharacterConcept.SOLDIER,
        50: CharacterConcept.ASCETIC,
        54: CharacterConcept.CRUSADER,
        66: CharacterConcept.URBAN_TRACKER,
        72: CharacterConcept.UNDER_WORLDER,
        83: CharacterConcept.SCIENTIST,
        90: CharacterConcept.TRADESMAN,
        98: CharacterConcept.BUSINESSMAN,
    }

    # WHEN member is selected by a number between 1-100
    for value, member in value_map.items():
        result = CharacterConcept.get_member_by_value(value)

        # THEN return the correct member
        assert isinstance(result, CharacterConcept)
        assert result == member


@pytest.mark.no_db
def test_trait_category_enum():
    """Test the TraitCategory enum."""
    assert TraitCategory.PHYSICAL.get_all_class_trait_names(CharClass.MORTAL) == [
        "Strength",
        "Dexterity",
        "Stamina",
    ]

    assert TraitCategory.TALENTS.get_all_class_trait_names(CharClass.WEREWOLF) == [
        "Alertness",
        "Athletics",
        "Brawl",
        "Dodge",
        "Empathy",
        "Expression",
        "Intimidation",
        "Leadership",
        "Streetwise",
        "Subterfuge",
        "Primal-Urge",
    ]


@pytest.mark.no_db
def test_char_class_random_member():
    """Test the CharClass enum."""
    for _ in range(50):
        # WHEN a random member of CharClass is selected
        result = CharClass.random_member()

        # THEN return a CharClass
        assert isinstance(result, CharClass)
        assert result != CharClass.NONE
        assert result != CharClass.OTHER


@pytest.mark.no_db
def test_char_class_get_member_by_value():
    """Test the CharClass enum get_member_by_value method."""
    # GIVEN a CharClass member
    value_map: dict[int, CharClass] = {
        1: CharClass.MORTAL,
        32: CharClass.MORTAL,
        62: CharClass.VAMPIRE,
        71: CharClass.WEREWOLF,
        75: CharClass.MAGE,
        80: CharClass.GHOUL,
        85: CharClass.CHANGELING,
        93: CharClass.HUNTER,
        98: CharClass.SPECIAL,
    }

    # WHEN member is selected by a number between 1-100
    for value, member in value_map.items():
        result = CharClass.get_member_by_value(value)

        # THEN return the correct member
        assert isinstance(result, CharClass)
        assert result == member

    # WHEN a number outside the range is selected
    # THEN raise a ValueError
    with pytest.raises(ValueError, match="Value 101 not found in any CharClass range"):
        CharClass.get_member_by_value(101)


@pytest.mark.no_db
def test_char_class_playable_classes():
    """Test the CharClass enum playable_classes method."""
    # WHEN the playable_classes method is called
    result = CharClass.playable_classes()

    # THEN return a list of only CharClass members
    assert CharClass.NONE not in result
    assert CharClass.COMMON not in result
    assert CharClass.OTHER not in result
    assert CharClass.SPECIAL in result
    assert CharClass.MORTAL in result


@pytest.mark.no_db
def test_hunter_creed_random_member():
    """Test the HunterCreed enum."""
    for _ in range(50):
        random = HunterCreed.random_member()
        assert HunterCreed[random.name] == random


@pytest.mark.no_db
def test_hunter_creed_get_member_by_value():
    """Test the HunterCreed enum get_member_by_value method."""
    # GIVEN a HunterCreed member
    value_map: dict[int, CharClass] = {
        1: HunterCreed.DEFENDER,
        18: HunterCreed.INNOCENT,
        35: HunterCreed.JUDGE,
        51: HunterCreed.MARTYR,
        65: HunterCreed.REDEEMER,
        80: HunterCreed.AVENGER,
        95: HunterCreed.VISIONARY,
    }

    # WHEN member is selected by a number between 1-100
    for value, member in value_map.items():
        result = HunterCreed.get_member_by_value(value)

        # THEN return the correct member
        assert isinstance(result, HunterCreed)
        assert result == member
