"""Helper functions for Valentina."""
from collections import defaultdict
from copy import deepcopy

from numpy.random import default_rng

from valentina.models.constants import (
    COMMON_TRAITS,
    DICEROLL_THUBMS,
    HUNTER_TRAITS,
    MAGE_TRAITS,
    VAMPIRE_TRAITS,
    WEREWOLF_TRAITS,
    MaxTraitValue,
    XPMultiplier,
    XPNew,
)

_rng = default_rng()


def merge_dictionaries(
    dict_list: list[dict[str, list[str]]], flat_list: bool = False
) -> dict[str, list[str]] | list[str]:
    """Merges a list of dictionaries into a single dictionary."""
    result: defaultdict[str, list[str]] = defaultdict(list)

    for d in dict_list:
        for key, value in d.items():
            if key in result:
                result[key].extend([item for item in value if item not in result[key]])
            else:
                result[key].extend(value)

    if flat_list:
        # Flattens the dictionary to a single list, while removing duplicates
        return list({item for sublist in result.values() for item in sublist})

    return dict(result)


def all_traits_from_constants(flat_list: bool = False) -> dict[str, list[str]] | list[str]:
    """Return all traits from the constants as a dictionary inclusive of all classes."""
    trait_dicts = [COMMON_TRAITS, MAGE_TRAITS, VAMPIRE_TRAITS, WEREWOLF_TRAITS, HUNTER_TRAITS]

    all_traits: dict[str, list[str]] = {}
    for dictionary in trait_dicts:
        for category, traits in dictionary.items():
            if category in all_traits:
                all_traits[category].extend(traits)
            else:
                all_traits[category] = traits

    if flat_list:
        return list({y for x in all_traits.values() for y in x})

    return all_traits


def diceroll_thumbnail(outcome: str) -> str:
    """Take a string and return a random gif url."""
    for category, thumbnails in DICEROLL_THUBMS.items():
        if category.lower() == outcome.lower():
            return thumbnails[_rng.integers(0, len(thumbnails))]

    return None


def extend_common_traits_with_class(char_class: str) -> dict[str, list[str]]:
    """Extends the common traits with the traits for a class."""
    complete_traits = deepcopy(COMMON_TRAITS)

    class_traits = {}
    match char_class.lower():
        case "mage":
            class_traits = deepcopy(MAGE_TRAITS)
        case "vampire":
            class_traits = deepcopy(VAMPIRE_TRAITS)
        case "werewolf":
            class_traits = deepcopy(WEREWOLF_TRAITS)
        case "hunter":
            class_traits = deepcopy(HUNTER_TRAITS)

    for category, traits in class_traits.items():
        if category in complete_traits:
            complete_traits[category].extend(traits)
        else:
            complete_traits[category] = traits

    return complete_traits


def normalize_to_db_row(row: str) -> str:
    """Takes a string and returns a normalized version of it for use as a row in the database."""
    return row.replace("-", "_").replace(" ", "_").lower()


def num_to_circles(num: int = 0, maximum: int = 5) -> str:
    """Return the emoji corresponding to the number. When `num` is greater than `maximum`, the `maximum` is increased to `num`.

    Args:
        num (int, optional): The number to convert. Defaults to 0.
        maximum (int, optional): The maximum number of circles. Defaults to 5.

    Returns:
        str: A string of circles and empty circles. i.e. `●●●○○`
    """
    if num is None:
        num = 0
    if maximum is None:
        maximum = 5
    if num > maximum:
        maximum = num

    return "●" * num + "○" * (maximum - num)


def get_max_trait_value(trait: str, is_custom_trait: bool = False) -> int | None:
    """Get the maximum value for a trait by looking up the trait in the XPMultiplier enum.

    Args:
        trait (str): The trait to get the max value for.
        is_custom_trait (bool, optional): Whether the trait is a custom trait. Defaults to False.

    Returns:
        int | None: The maximum value for the trait or None if the trait is a custom trait and no default for it's parent category exists.

    """
    # Some traits have their own max value. Check for those first.
    if trait.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[trait.upper()].value

    # Try to find the max value by looking up the parent key of the trait
    all_constants = [COMMON_TRAITS, MAGE_TRAITS, VAMPIRE_TRAITS, WEREWOLF_TRAITS, HUNTER_TRAITS]
    all_traits = merge_dictionaries(all_constants, flat_list=False)

    if isinstance(all_traits, dict):
        for category, traits in all_traits.items():
            if (
                trait.lower() in [x.lower() for x in traits]
                and category.upper() in MaxTraitValue.__members__
            ):
                return MaxTraitValue[category.upper()].value

    if is_custom_trait:
        return None

    return MaxTraitValue.DEFAULT.value


def get_trait_multiplier(trait: str) -> int:
    """Get the experience multiplier associated with a trait for use when upgrading.

    Args:
        trait (str): The trait to get the cost for.

    Returns:
        int: The multiplier associated with the trait.
    """
    # Some traits have their own max value. Check for those first.
    if trait.upper() in XPMultiplier.__members__:
        return XPMultiplier[trait.upper()].value

    # Try to find the multiplier by looking up the parent key of the trait
    all_constants = [COMMON_TRAITS, MAGE_TRAITS, VAMPIRE_TRAITS, WEREWOLF_TRAITS, HUNTER_TRAITS]
    all_traits = merge_dictionaries(all_constants, flat_list=False)

    if isinstance(all_traits, dict):
        for category, traits in all_traits.items():
            if (
                trait.lower() in [x.lower() for x in traits]
                and category.upper() in XPMultiplier.__members__
            ):
                return XPMultiplier[category.upper()].value

    # Return the default value
    return XPMultiplier.DEFAULT.value


def get_trait_new_value(trait: str) -> int:
    """Get the experience cost of the first dot for a wholly new trait from the XPNew enum.

    Args:
        trait (str): The trait to get the cost for.

    Returns:
        int: The cost of the first dot of the trait.
    """
    # Some traits have their own value. Check for those first.
    if trait.upper() in XPNew.__members__:
        return XPNew[trait.upper()].value

    # Try to find the cost by looking up the parent key of the trait
    all_constants = [COMMON_TRAITS, MAGE_TRAITS, VAMPIRE_TRAITS, WEREWOLF_TRAITS, HUNTER_TRAITS]
    all_traits = merge_dictionaries(all_constants, flat_list=False)

    if isinstance(all_traits, dict):
        for category, traits in all_traits.items():
            if (
                trait.lower() in [x.lower() for x in traits]
                and category.upper() in XPNew.__members__
            ):
                return XPNew[category.upper()].value

    # Return the default value
    return XPNew.DEFAULT.value
