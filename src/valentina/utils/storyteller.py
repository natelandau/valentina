"""Helper utilities for building storyteller characters."""

import random

from numpy import int32
from numpy.random import default_rng

from valentina.models.database import Trait
from valentina.utils.helpers import fetch_clan_disciplines, get_max_trait_value, round_trait_value

_rng = default_rng()
_fighter_traits = ["Melee", "Firearms", "Alertness", "Athletics", "Brawl", "Dodge", "Stealth"]
_leader_traits = ["Empathy", "Leadership", "Performance", "Subterfuge", "Intimidation"]
_doer_traits = [
    "Crafts",
    "Drive",
    "Security",
    "Larceny",
    "Survival",
    "Computer",
    "Investigation",
    "Medicine",
    "Science",
]


def __storyteller_attributes(
    attributes: dict[str, list[Trait]], level: str, specialty: str
) -> dict[int, int]:
    """Set attribute values for storyteller characters.  Characters begin with 7/5/3 dots per attribute category.  The storyteller character's level determines the number of dots added to each attribute category.  The storyteller character's specialty determines which attribute category gets the most dots.  The remaining dots are randomly distributed to the other attribute categories.

    Args:
        attributes (dict[str, list[Trait]]): A dictionary of attributes.
        level (str): The storyteller character's level.
        specialty (str): The storyteller character's specialty.

    Returns:
        dict[int, int]: A dictionary of trait values.

    """
    trait_values: dict[int, int] = {}

    match level:
        case "Weakling":
            attribute_adjustment = 0
        case "Average":
            attribute_adjustment = 0
        case "Strong":
            attribute_adjustment = 1
        case "Super":
            attribute_adjustment = 2

    # Attributes
    attribute_values = {"primary": [3, 2, 2], "secondary": [2, 2, 1], "tertiary": [1, 1, 1]}

    while len(attributes) > 0:
        cat: str = random.choice([x for x in attributes])

        if specialty == "Fighter":
            if cat == "Physical":
                vals: str = "primary"
            else:
                vals = random.choice([x for x in attribute_values if x != "primary"])
        elif specialty == "Thinker":
            if cat == "Mental":
                vals = "primary"
            else:
                vals = random.choice([x for x in attribute_values if x != "primary"])

        vals = random.choice([x for x in attribute_values])

        for t in attributes[cat]:
            value = attribute_values[vals].pop(0)
            trait_values[t.id] = round_trait_value(value + attribute_adjustment, 5)
            if len(attribute_values[vals]) == 0:
                del attribute_values[vals]

        del attributes[cat]

    return trait_values


def __storyteller_disciplines(
    discipline_list: list[Trait], level: str, clan: str
) -> dict[int, int]:
    """Set discipline values for storyteller vampire characters.  Each clan has three associated disciplines. For each clan discipline, the character gets a minimum.  The remaining disciplines are randomly selected from the list of all disciplines.  The number of disciplines and their values are determined by the character's level.

    Args:
        discipline_list (list[Trait]): A list of all disciplines.
        level (str): The storyteller character's level.
        clan (str): The storyteller character's clan.

    Returns:
        dict[int, int]: A dictionary of trait values.
    """
    trait_values: dict[int, int] = {}

    clan_disciplines = [x for x in discipline_list if x.name in fetch_clan_disciplines(clan)]
    non_clan_disciplines = []

    # Add more disciplines based on level
    if level == "Strong":
        non_clan_disciplines = random.sample(
            [x for x in discipline_list if x.name not in clan_disciplines], 1
        )

    if level == "Super":
        non_clan_disciplines = random.sample(
            [x for x in discipline_list if x.name not in clan_disciplines], 3
        )

    # Set normal distribution values based on characters level
    mean, distribution = __normal_distribution_values(level)

    # Set the trait values from a normal distribution
    values = [
        round_trait_value(x, 6)
        for x in _rng.normal(
            mean, distribution, len(clan_disciplines) + len(non_clan_disciplines)
        ).astype(int32)
    ]

    for discipline in clan_disciplines:
        value = values.pop(0)

        if level in ["Strong", "Super"]:
            value = round_trait_value(value + 1, 6)

        if level in ["Weakling", "Average"] and value == 0:
            value = 1

        trait_values[discipline.id] = value

    for discipline in non_clan_disciplines:
        value = values.pop(0)

        if level in ["Super"]:
            value = round_trait_value(value + 1, 6)

        trait_values[discipline.id] = value

    return trait_values


def __normal_distribution_values(level: str) -> tuple[float, float]:
    """Return the mean and distribution for a level.  To reach more about this model, see https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.normal.html.

    Args:
        level (str): The storyteller character's level.

    Returns:
        tuple[float, float]: A tuple containing the mean and distribution values.

    Examples:
        >>> __normal_distribution_values("Weakling")
        (1.0, 2.0)
    """
    match level:
        case "Weakling":
            mean = 1.0
            distribution = 2.0
        case "Average":
            mean = 1.5
            distribution = 2.0
        case "Strong":
            mean = 2.5
            distribution = 2.0
        case "Super":
            mean = 3.0
            distribution = 2.0

    return (mean, distribution)


def storyteller_character_traits(
    traits: list[Trait], level: str, specialty: str, clan: str | None = None
) -> dict[int, int]:
    """Create a storyteller character."""
    traits_by_category: dict[str, list[Trait]] = {}
    trait_values: dict[int, int] = {}
    attributes: dict[str, list[Trait]] = {}
    disciplines: list[Trait] = []

    # Parse the traits into categories for easier processing
    for trait in traits:
        # Build a list of attributes
        if trait.category.name in ["Physical", "Social", "Mental"]:
            if trait.category.name not in attributes:
                attributes[trait.category.name] = []

            attributes[trait.category.name].append(trait)
            continue

        # Build a list of disciplines
        if trait.category.name == "Disciplines":
            disciplines.append(trait)
            continue

        # Build list of all other traits
        if trait.category.name not in traits_by_category:
            traits_by_category[trait.category.name] = []

        traits_by_category[trait.category.name].append(trait)

    # Add attributes trait values
    trait_values.update(__storyteller_attributes(attributes, level, specialty))

    # Add disciplines trait values
    trait_values.update(__storyteller_disciplines(disciplines, level, clan))

    # Set normal distribution values based on characters level
    mean, distribution = __normal_distribution_values(level)

    for category, traits in traits_by_category.items():
        values = [
            round_trait_value(x, get_max_trait_value(trait.name, category))
            for x in _rng.normal(mean, distribution, len(traits)).astype(int32)
        ]

        for trait in traits:
            value = values.pop(0)

            if level in ["Strong", "Super"] and (
                (specialty == "Fighter" and trait.name in _fighter_traits)
                or (specialty == "Leader" and trait.name in _leader_traits)
                or (specialty == "Doer" and trait.name in _doer_traits)
            ):
                round_trait_value(value + 1, get_max_trait_value(trait.name, category))

            trait_values[trait.id] = value

    return trait_values
