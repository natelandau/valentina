"""Helper functions for Valentina."""
from valentina.models.constants import COMMON_TRAITS, MaxTraitValue, XPMultiplier, XPNew
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


def get_max_trait_value(trait: str) -> int:
    """Get the maximum value for a trait by looking up the trait in the XPMultiplier enum.

    Args:
        trait (str): The trait to get the max value for.

    Returns:
        int: The maximum value for the trait.
    """
    # Some traits have their own max value. Check for those first.
    if trait.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[trait.upper()].value

    # Try to find the cost by looking up the parent key of the trait
    for category, traits in COMMON_TRAITS.items():
        if (
            trait.lower() in [x.lower() for x in traits]
            and category.upper() in MaxTraitValue.__members__
        ):
            return MaxTraitValue[category.upper()].value

    # Return the default value
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

    # Try to find the cost by looking up the parent key of the trait
    for category, traits in COMMON_TRAITS.items():
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
    for category, traits in COMMON_TRAITS.items():
        if trait.lower() in [x.lower() for x in traits] and category.upper() in XPNew.__members__:
            return XPNew[category.upper()].value

    # Return the default value
    return XPNew.DEFAULT.value
