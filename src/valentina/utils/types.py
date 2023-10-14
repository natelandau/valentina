# mypy: disable-error-code="name-defined"
"""Custom Types for Valentina."""
from typing_extensions import TypedDict

### TypedDicts ###


class CharacterClassDict(TypedDict):
    """Type for CharClassType info sub-dictionary."""

    name: str
    range: tuple[int, int]
    description: str
    playable: bool
    chargen_background_dots: int  # backgrounds used in chargen


class CharSheetSectionDict(TypedDict):
    """Type for CharSheetSection info Enum."""

    name: str
    order: int


class TraitCategoriesDict(TypedDict):
    """Type for TraitCategories Enum."""

    classes: list["CharacterClass"]  # noqa: F821 # type: ignore
    name: str
    order: int
    section: "CharSheetSection"  # noqa: F821 # type: ignore
    show_zero: bool
    COMMON: list[str]
    MORTAL: list[str]
    VAMPIRE: list[str]
    WEREWOLF: list[str]
    MAGE: list[str]
    GHOUL: list[str]
    CHANGELING: list[str]
    HUNTER: list[str]
    SPECIAL: list[str]


class CharConceptDict(TypedDict):
    """Type for concept info Enum."""

    abilities: list[dict[str, str | int | list[tuple[str, str | int]]]]
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
