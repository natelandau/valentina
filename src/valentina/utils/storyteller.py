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

    # Attribute adjustment based on level
    attribute_adjustment_map = {"Weakling": 0, "Average": 0, "Strong": 1, "Super": 2}
    attribute_adjustment = attribute_adjustment_map.get(level, 0)

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

    def __adjust_value(value: int, level: str) -> int:
        """Adjust discipline value based on character level."""
        if level in ["Strong", "Super"]:
            value = value + 1

        if level == "Weakling" and value > 3:  # noqa: PLR2004
            value = 3

        elif value == 0:
            value = 1

        return round_trait_value(value, 5)

    trait_values: dict[int, int] = {}

    level_discipline_count_map = {"Weakling": 0, "Average": 0, "Strong": 1, "Super": 3}
    clan_disciplines = [x for x in discipline_list if x.name in fetch_clan_disciplines(clan)]

    # Grab extra disciplines based on level
    non_clan_disciplines = random.sample(
        [x for x in discipline_list if x not in clan_disciplines], level_discipline_count_map[level]
    )

    # Set normal distribution values based on characters level
    mean, distribution = __normal_distribution_values(level)

    # Set the trait values from a normal distribution
    values = [
        __adjust_value(x, level)
        for x in _rng.normal(
            mean, distribution, len(clan_disciplines) + len(non_clan_disciplines)
        ).astype(int32)
    ]

    for discipline in clan_disciplines + non_clan_disciplines:
        value = values.pop(0)
        if value == 0:
            value = 1

        trait_values[discipline.id] = value

    return trait_values


def __normal_distribution_values(level: str) -> tuple[float, float]:
    """Return the mean and standard deviation for a character's attribute values, based on the character's level. The attribute values are modeled as a normal distribution where the mean and standard deviation vary by level.

    The function uses the numpy library's random number generator to generate attribute values. For more information about this model, see the numpy documentation at https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.normal.html.


    Args:
        level (str): The character's level. This should be one of the following strings:
        "Weakling", "Average", "Strong", "Super".

    Returns:
        tuple[float, float]: A tuple containing the mean (first element) and standard deviation
        (second element) for the character's attribute values. If an unrecognized level is provided,
        the function returns (0, 0).

    Examples:
        >>> __normal_distribution_values("Weakling")
        (1.0, 2.0)

        >>> __normal_distribution_values("Super")
        (3.0, 2.0)
    """
    level_distribution_map = {
        "Weakling": (1.0, 2.0),
        "Average": (1.5, 2.0),
        "Strong": (2.5, 2.0),
        "Super": (3.0, 2.0),
    }

    return level_distribution_map.get(level, (0, 0))  # return (0, 0) for unrecognized levels


def storyteller_character_traits(
    traits: list[Trait], level: str, specialty: str, clan: str | None = None
) -> dict[int, int]:
    """Create a storyteller character by generating trait values based on the provided traits, level, specialty, and clan.

    The function generates trait values following a normal distribution, where the mean and standard deviation of the distribution depend on the character's level. The mean and standard deviation for each level are determined by the __normal_distribution_values helper function.

    After generating a list of potential trait values, the function assigns each trait a value. The assignment process varies based on the trait's category (Physical, Social, Mental, Disciplines) and the character's level and specialty.

    Args:
        traits (list[Trait]): A list of Trait objects representing the character's potential traits.
        level (str): The storyteller character's level which determines the mean and standard deviation of the normal distribution used to generate trait values.
        specialty (str): The storyteller character's specialty. This can influence which traits receive higher values.
        clan (str | None): The storyteller character's clan. Defaults to None. Some traits (disciplines) are specific to certain clans.

    Returns:
        dict[int, int]: A dictionary mapping trait ids to their corresponding values.
    """

    def __specialty_traits_match(specialty: str, trait_name: str) -> bool:
        """Check if a trait matches with the specialty.

        Args:
            specialty (str): The storyteller character's specialty.
            trait_name (str): Name of the trait.

        Returns:
            bool: True if the trait matches the specialty, False otherwise.
        """
        specialty_traits = {
            "Fighter": _fighter_traits,
            "Leader": _leader_traits,
            "Doer": _doer_traits,
        }
        return trait_name in specialty_traits.get(specialty, [])

    # Parse the traits into categories for easier processing
    traits_by_category: dict[str, list[Trait]] = {trait.category.name: [] for trait in traits}
    for trait in traits:
        traits_by_category[trait.category.name].append(trait)

    # Calculate attribute and discipline trait values
    attributes = {
        cat: traits
        for cat, traits in traits_by_category.items()
        if cat in ["Physical", "Social", "Mental"]
    }
    trait_values = __storyteller_attributes(attributes, level, specialty)
    if "Disciplines" in traits_by_category:
        trait_values.update(
            __storyteller_disciplines(traits_by_category["Disciplines"], level, clan)
        )

    # Set normal distribution values based on characters level
    mean, distribution = __normal_distribution_values(level)

    for category, traits in traits_by_category.items():
        if category in ["Physical", "Social", "Mental", "Disciplines"]:
            continue  # Skip attributes and disciplines as they are already processed

        # Calculate trait values
        values = [
            round_trait_value(x, get_max_trait_value(trait.name, category))
            for x in _rng.normal(mean, distribution, len(traits)).astype(int32)
        ]

        for trait in traits:
            value = values.pop(0)
            if level in ["Strong", "Super"] and __specialty_traits_match(specialty, trait.name):
                value = round_trait_value(value + 1, get_max_trait_value(trait.name, category))
            trait_values[trait.id] = value

    return trait_values
