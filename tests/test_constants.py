# type: ignore
"""Test the constants module."""

from valentina.constants import CharacterConcept, CharClass, TraitCategory, VampireClan


def test_random_vampire_clan() -> None:
    """Test the random_vampire_clan function."""
    result = VampireClan.random_member()
    assert result.name in VampireClan.__members__


def test_character_concept_enum():
    """Test the CharacterConcept enum."""
    assert CharacterConcept.get_member_by_value(8) == CharacterConcept.BERSERKER

    random = CharacterConcept.random_member()
    assert CharacterConcept[random.name] == random


def test_trait_category_enum():
    """Test the TraitCategory enum."""
    assert TraitCategory.PHYSICAL.get_trait_list(CharClass.MORTAL) == [
        "Strength",
        "Dexterity",
        "Stamina",
    ]

    assert TraitCategory.TALENTS.get_trait_list(CharClass.WEREWOLF) == [
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
