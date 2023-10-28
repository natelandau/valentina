# mypy: disable-error-code="name-defined"
"""Custom Types for Valentina."""
from typing import TypedDict

### TypedDicts ###


class HunterCreedDict(TypedDict):
    """Type for Hunter Creed sub-dictionary."""

    name: str
    description: str
    conviction: int
    specific_abilities: list[str]
    ability_specialty: "CharClass"  # noqa: F821 # type: ignore
    attribute_specialty: "CharClass"  # noqa: F821 # type: ignore
    edges: list[str]
    range: tuple[int, int]


class CharClassDict(TypedDict):
    """Type for CharClass info sub-dictionary."""

    name: str
    range: tuple[int, int]
    description: str
    playable: bool
    chargen_background_dots: int  # backgrounds used in chargen


class ConceptAbilityDict(TypedDict):
    """Type for CharacterConcept.ability sub-dictionary."""

    name: str
    description: str
    traits: list[tuple[str, int, str]]
    custom_sections: list[tuple[str, str]]


class CharSheetSectionDict(TypedDict):
    """Type for CharSheetSection info Enum."""

    name: str
    order: int


class CharacterConceptDict(TypedDict):
    """Type for concept info Enum."""

    abilities: list[dict[str, str | int | list[tuple[str, str | int]]]]
    ability_specialty: "CharClass"  # noqa: F821 # type: ignore
    attribute_specialty: "CharClass"  # noqa: F821 # type: ignore
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
