"""Helper functions for Valentina."""
import re

import discord
from numpy.random import default_rng

from valentina.models.constants import (
    CLAN_DISCIPLINES,
    DICEROLL_THUBMS,
    MaxTraitValue,
    RollResultType,
    XPMultiplier,
    XPNew,
)

_rng = default_rng()


def fetch_clan_disciplines(clan: str) -> list[str]:
    """Fetch the disciplines for a clan.

    Examples:
        >>> fetch_clan_disciplines("toreador")
        ['Auspex', 'Celerity', 'Presence']


    """
    return CLAN_DISCIPLINES[clan.title()]


def diceroll_thumbnail(ctx: discord.ApplicationContext, result: RollResultType) -> str:
    """Take a string and return a random gif url."""
    thumb_list = DICEROLL_THUBMS[result.name]
    database_thumbs = ctx.bot.guild_svc.fetch_roll_result_thumbs(ctx)  # type: ignore [attr-defined]
    for category, thumbnails in database_thumbs.items():
        if category.lower() == result.name.lower():
            thumb_list.extend(thumbnails)

    return thumb_list[_rng.integers(0, len(thumb_list))]


def get_max_trait_value(trait: str, category: str, is_custom_trait: bool = False) -> int | None:
    """Get the maximum value for a trait by looking up the trait in the XPMultiplier enum.

    Args:
        trait (str): The trait to get the max value for.
        category (str): The category of the trait.
        is_custom_trait (bool, optional): Whether the trait is a custom trait. Defaults to False.

    Returns:
        int | None: The maximum value for the trait or None if the trait is a custom trait and no default for it's parent category exists.

    Examples:
        >>> get_max_trait_value("Dominate", "Disciplines")
        5

        >>> get_max_trait_value("Willpower", "Other")
        10

        >>> get_max_trait_value("xxx", "xxx")
        5

        >>> get_max_trait_value("xxx", "xxx", True)


    """
    # Some traits have their own max value. Check for those first.
    if trait.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[trait.upper()].value

    # Try to find the max value by looking up the category of the trait
    if category.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[category.upper()].value

    if is_custom_trait:
        return None

    return MaxTraitValue.DEFAULT.value


def get_trait_multiplier(trait: str, category: str) -> int:
    """Get the experience multiplier associated with a trait for use when upgrading.

    Args:
        trait (str): The trait to get the cost for.
        category (str): The category of the trait.

    Returns:
        int: The multiplier associated with the trait.

    >>> get_trait_multiplier("Dominate", "Disciplines")
    7

    >>> get_trait_multiplier("Humanity", "Universal")
    2

    >>> get_trait_multiplier("xxx", "xxx")
    2
    """
    if trait.upper() in XPMultiplier.__members__:
        return XPMultiplier[trait.upper()].value

    if category.upper() in XPMultiplier.__members__:
        return XPMultiplier[category.upper()].value

    return XPMultiplier.DEFAULT.value


def get_trait_new_value(trait: str, category: str) -> int:
    """Get the experience cost of the first dot for a wholly new trait from the XPNew enum.

    Args:
        trait (str): The trait to get the cost for.
        category (str): The category of the trait.

    Returns:
        int: The cost of the first dot of the trait.

    >>> get_trait_new_value("Dominate", "Disciplines")
    10

    >>> get_trait_new_value("Talents", "")
    3

    >>> get_trait_new_value("XXX", "XXX")
    1
    """
    if trait.upper() in XPNew.__members__:
        return XPNew[trait.upper()].value

    if category.upper() in XPNew.__members__:
        return XPNew[category.upper()].value

    return XPNew.DEFAULT.value


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


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun.

    Args:
        value (int): The number of the noun.
        noun (str): The noun to pluralize.

    >>> pluralize(1, "die")
    'die'

    >>> pluralize(2, "die")
    'dice'

    >>> pluralize(2, "Die")
    'Dice'

    >>> pluralize(3, "DIE")
    'DICE'

    >>> pluralize(1, "mess")
    'mess'

    >>> pluralize(2, "specialty")
    'specialties'

    >>> pluralize(2, "fry")
    'fries'

    >>> pluralize(2, "botch")
    'botches'

    >>> pluralize(2, "critical")
    'criticals'
    """
    nouns = {
        "success": "successes",
        "die": "dice",
        "failure": "failures",
    }

    if value != 1:
        is_title_case = False
        is_all_caps = False
        if re.search("^[A-Z][a-z]+$", noun):
            is_title_case = True

        if re.search("^[A-Z]+$", noun):
            is_all_caps = True

        if noun.lower() in nouns:
            plural = nouns[noun.lower()]

        elif re.search("[sxz]$", noun) or re.search("[^aeioudgkprt]h$", noun):
            plural = re.sub("$", "es", noun)

        elif re.search("[^aeiou]y$", noun):
            plural = re.sub("y$", "ies", noun)
        else:
            plural = noun + "s"

        if is_title_case:
            return plural.title()
        if is_all_caps:
            return plural.upper()

        return plural

    return noun
