"""Helper functions for Valentina."""

import io
import random
from datetime import datetime, timezone
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientSession
from loguru import logger

from valentina.constants import (
    MaxTraitValue,
    XPMultiplier,
    XPNew,
)
from valentina.utils import errors


def adjust_sum_to_match_total(
    values: list[int], total: int, max_value: int | None = None, min_value: int = 0
) -> list[int]:
    """Adjust the sum of a list of integers to match a given total.

    The function modifies the list values randomly to match the desired total, ensuring
    individual values remain within set bounds.

    Args:
        values (List[int]): List of integers to adjust.
        total (int): Desired sum of the list after adjustment.
        max_value (int | None): Maximum allowable value for each integer. If None, there's no upper bound.
        min_value (int): Minimum allowable value for each integer. Defaults to 0.

    Returns:
        List[int]: Adjusted list with the sum matching the desired total.
    """
    current_sum = sum(values)
    delta = total - current_sum

    # Adjust the sum to reach the desired total
    while delta != 0:
        if delta > 0:
            # Identify indexes we can give a point to
            valid_indices = [i for i, x in enumerate(values) if max_value is None or x < max_value]
        else:
            valid_indices = [i for i, x in enumerate(values) if x > min_value]

        index_to_adjust = random.choice(valid_indices) if valid_indices else None
        if index_to_adjust is not None:
            values[index_to_adjust] += 1 if delta > 0 else -1
            delta += -1 if delta > 0 else 1
        else:
            logger.warning("No valid index found to adjust. Breaking the loop.")
            break

    # Ensure the min_value is respected
    while any(x < min_value for x in values):
        # Identify indexes we can take a point from
        valid_indices = [i for i, x in enumerate(values) if x > min_value]
        if valid_indices:
            # Identify the index we can give a point to
            index_to_adjust = next((i for i, x in enumerate(values) if x < min_value), None)

            # Adjust the values
            values[index_to_adjust] += 1
            values[random.choice(valid_indices)] -= 1

    # Ensure the max_value is respected
    while max_value is not None and any(x > max_value for x in values):
        # Identify indexes we can give a point to
        valid_indices = [i for i, x in enumerate(values) if x < max_value]
        if valid_indices:
            # Identify the index we can take a point from
            index_to_adjust = next((i for i, x in enumerate(values) if x > max_value), None)

            # Adjust the values
            values[index_to_adjust] -= 1
            values[random.choice(valid_indices)] += 1

    return values


async def fetch_random_name(
    gender: str | None = None, country: str = "us", results: int = 1
) -> list[tuple[str, str]] | tuple[str, str]:
    """Fetch a random name from the randomuser.me API.

    Args:
        country (str, optional): The country to fetch the name from. Defaults to "us".
        results (int, optional): The number of results to fetch. Defaults to 1.
        gender (str, optional): The gender of the name to fetch. Defaults to None

    Returns:
        list[tuple[str, str]] | tuple[str, str]: A list of tuples containing the first and last name. If only one result, a single tuple is returned.

    """
    if not gender:
        gender = random.choice(["male", "female"])

    params = {"gender": gender, "nat": country, "inc": "name", "results": results}
    url = f"https://randomuser.me/api/?{urlencode(params)}"

    async with ClientSession() as session, session.get(url) as res:
        if 300 > res.status >= 200:  # noqa: PLR2004
            data = await res.json()

            result = [
                (result["name"]["first"], result["name"]["last"]) for result in data["results"]
            ]

            if len(result) == 1:
                return result[0]

            return result

    return [("John", "Doe")]


def divide_into_three(total: int) -> list[int]:
    """Divide an integer into three randomly sized integers that add up to the original integer.

    Args:
        total (int): The original integer value to be divided.

    Returns:
        list[int, int, int]: A list containing three integers that add up to the original integer.
    """
    if total <= 2:  # noqa: PLR2004
        msg = "Total should be greater than 2 to divide it into three integers."
        raise ValueError(msg)

    # Generate split1
    split1 = random.randint(1, total - 2)

    # Generate split2 such that split1 + split2 is less than total
    split2 = random.randint(1, total - split1)

    # Calculate the three segments
    segment1 = split1
    segment2 = split2
    segment3 = total - (split1 + split2)

    if segment1 + segment2 + segment3 != total:
        msg = f"Segments do not add up to total. Segments: {segment1}, {segment2}, {segment3}. Total: {total}"
        raise ValueError(msg)

    return [segment1, segment2, segment3]


def get_max_trait_value(trait: str, category: str) -> int | None:
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
    """
    # Some traits have their own max value. Check for those first.
    if trait.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[trait.upper()].value

    # Try to find the max value by looking up the category of the trait
    if category.upper() in MaxTraitValue.__members__:
        return MaxTraitValue[category.upper()].value

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


async def fetch_data_from_url(url: str) -> io.BytesIO:
    """Fetch data from a URL to be used to upload to Amazon S3."""
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        if resp.status != 200:  # noqa: PLR2004
            msg = f"Could not fetch data from {url}"
            raise errors.URLNotAvailableError(msg)

        return io.BytesIO(await resp.read())


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


def truncate_string(text: str, max_length: int = 1000) -> str:
    """Truncate a string to a maximum length.

    Args:
        text (str): The string to truncate.
        max_length (int, optional): The maximum length of the string. Defaults to 1000.

    Returns:
        str: The truncated string.

    Examples:
        >>> truncate_string("This is a test", 10)
        'This i...'

        >>> truncate_string("This is a test", 100)
        'This is a test'
    """
    if len(text) > max_length:
        return text[: max_length - 4] + "..."
    return text


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)
