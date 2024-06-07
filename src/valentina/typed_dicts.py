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


class RNGSpecialtyDict(TypedDict):
    """Type for RNG specialty sub-dictionary."""

    traits: list[str]
