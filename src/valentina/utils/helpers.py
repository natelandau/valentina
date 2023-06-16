"""Helper functions for Valentina."""
from valentina.models.constants import GROUPED_TRAITS, MaxTraitValue, XPNew, XPRaise
from valentina.models.database import Character


def normalize_row(row: str) -> str:
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


def format_traits(character: Character, traits: list[str], show_zeros: bool = True) -> str:
    """Return a string of traits to be added as the value of an embed field.

    Args:
        character (Character): The character to get the traits from.
        traits (list[str]): The traits to get from the character.
        show_zeros (bool, optional): Whether to show traits with a value of 0. Defaults to True.

    Returns:
        str: A string of traits to be added as the value of an embed field. In the format of:
            `trait_name: ●●●○○`
    """
    trait_list = []

    for t in traits:
        trait = normalize_row(t)
        max_value = get_max_trait_value(trait)

        if hasattr(character, trait):
            value = getattr(character, trait)
            if not show_zeros and (value == 0 or value is None):
                continue

            value = num_to_circles(value, max_value)
            trait_list.append(f"`{trait:13}: {value}`")

    return "\n".join(trait_list)


def find_parent_key(trait: str, grouped_traits: dict, lvl: int = 2) -> str:
    """Find the parent key of a given trait in a nested dictionary of grouped traits.

    Args:
        trait (str): The trait to find the parent key for.
        grouped_traits (dict): The nested dictionary of grouped traits.
        lvl (int, optional): The level of the nested dictionary to search. Defaults to 2.

    Returns:
        str: The parent key of the trait if found, the trait itself.

    Example:
        >>> find_parent_key("Strength", GROUPED_TRAITS, 2)
        'ATTRIBUTES'
    """
    for parent_key, categories in grouped_traits.items():
        for category, traits in categories.items():
            if trait in traits and lvl == 1:
                return category.upper()
            if trait in traits and lvl == 2:  # noqa: PLR2004
                return parent_key.upper()

    return trait.upper()


def get_max_trait_value(trait: str) -> int:
    """Get the maximum value for a trait."""
    # Try to find the cost by looking up the parent key of the trait
    for lvl in [2, 1]:
        trait_parent = find_parent_key(trait, GROUPED_TRAITS, lvl)
        if trait_parent in MaxTraitValue.__members__:
            return MaxTraitValue[trait_parent].value

    # If the parent key wasn't found, try to look up the trait itself
    if trait.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[trait.upper()].value

    return 5


def get_trait_multiplier(trait: str) -> int:
    """Gets the experience multiplier associated with a trait for use when upgrading.

    Args:
        trait (str): The trait to get the cost for.

    Returns:
        int: The multiplier associated with the trait.

    Raises:
        ValueError: If the trait or its parent key is not found in the XPRaise enum.
    """
    # Try to find the cost by looking up the parent key of the trait
    for lvl in [2, 1]:
        trait_parent = find_parent_key(trait, GROUPED_TRAITS, lvl)
        if trait_parent in XPRaise.__members__:
            return XPRaise[trait_parent].value

    # If the parent key wasn't found, try to look up the trait itself
    if trait.upper() in XPRaise.__members__:
        return XPRaise[trait.upper()].value

    # If the trait wasn't found, raise an error
    raise ValueError(f"Trait {trait} not found in XPRaise enum.")


def get_trait_new_value(trait: str) -> int:
    """Gets the multiplier associated with a trait for use when upgrading using experience."""
    # Try to find the cost by looking up the parent key of the trait
    for lvl in [2, 1]:
        trait_parent = find_parent_key(trait, GROUPED_TRAITS, lvl)
        if trait_parent in XPNew.__members__:
            return XPNew[trait_parent].value

    # If the parent key wasn't found, try to look up the trait itself
    if trait.upper() in XPNew.__members__:
        return XPNew[trait.upper()].value

    return 1
