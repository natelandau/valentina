"""Custom Types for Valentina."""
from typing_extensions import TypedDict

### TypedDicts ###


class CharacterClassDict(TypedDict):
    """Type for CharClassType info sub-dictionary."""

    name: str
    range: tuple[int, int]
    description: str


class CharConceptDict(TypedDict):
    """Type for concept info sub-dictionary."""

    abilities: list[dict[str, str]]
    ability_specialty: str
    attribute_specialty: str
    description: str
    examples: str
    name: str
    num_abilities: int
    range: tuple[int, int]
    specific_abilities: list[str]


class RNGSpecialtyDict(TypedDict):
    """Type for RNG specialty sub-dictionary."""

    traits: list[str]


class VampireClanDict(TypedDict):
    """Type for vampire clan sub-dictionary."""

    name: str
    disciplines: list[str]


class CharGenCategoryDict(TypedDict):
    """Type for character generation category sub-dictionary used in RNGTraitValues."""

    total_dots: int
    category: str
