# mypy: disable-error-code="name-defined"
"""Custom Types for Valentina."""
from typing_extensions import TypedDict

### TypedDicts ###


class CharacterClassDict(TypedDict):
    """Type for CharClassType info sub-dictionary."""

    name: str
    range: tuple[int, int]
    description: str


class TraitCategoriesDict(TypedDict):
    """Type for TraitCategories Enum."""

    classes: list["CharacterClass"]  # noqa: F821 # type: ignore
    name: str
    order: int


class CharConceptDict(TypedDict):
    """Type for concept info sub-dictionary."""

    abilities: list[dict[str, str | int]]
    ability_specialty: "CharacterClass"  # noqa: F821 # type: ignore
    attribute_specialty: "CharacterClass"  # noqa: F821 # type: ignore
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
    """Type for character generation category sub-dictionary used in CharacterTraitRandomizer."""

    total_dots: int
    category: str
