"""Helper functions for Valentina."""

import io
import random
from datetime import UTC, datetime
from urllib.parse import urlencode

from aiohttp import ClientSession
from numpy.random import default_rng

from valentina.constants import MaxTraitValue, XPMultiplier, XPNew
from valentina.utils import errors

_rng = default_rng()


def convert_int_to_emoji(num: int, markdown: bool = False) -> str:
    """Convert an integer to an emoji or a string.

    Args:
        num (int): The integer to convert.
        markdown (bool, optional): Whether to wrap numbers larger than emojis in markdown code. Defaults to False.

    Returns:
        str: The emoji corresponding to the integer.

    Examples:
        >>> convert_int_to_emoji(1)
        ':one:'

        >>> convert_int_to_emoji(10)
        ':keycap_ten:'

        >>> convert_int_to_emoji(11)
        '11'

        >>> convert_int_to_emoji(11, markdown=True)
        '`11`'
    """
    if -1 <= num <= 10:  # noqa: PLR2004
        return (
            str(num)
            .replace("10", ":keycap_ten:")
            .replace("0", ":zero:")
            .replace("1", ":one:")
            .replace("2", ":two:")
            .replace("3", ":three:")
            .replace("4", ":four:")
            .replace("5", ":five:")
            .replace("6", ":six:")
            .replace("7", ":seven:")
            .replace("8", ":eight:")
            .replace("9", ":nine:")
        )
    if markdown:
        return f"`{num}`"

    return str(num)


def random_num(ceiling: int = 100) -> int:
    """Get a random number between 1 and ceiling."""
    return _rng.integers(1, ceiling + 1)


async def fetch_random_name(
    gender: str | None = None, country: str = "us", results: int = 1
) -> list[tuple[str, str]] | tuple[str, str]:  # pragma: no cover
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


def divide_total_randomly(
    total: int, num: int, max_value: int | None = None, min_value: int = 0
) -> list[int]:
    """Divide a total into 'num' random segments whose sum equals the total.

    This function divides a given 'total' into 'num' elements, each with a random value.
    The sum of these elements will always equal 'total'. If 'max_value' is provided,
    no single element will be greater than this value. Additionally, no element will ever
    be less than or equal to 0.

    Args:
        total (int): The total sum to be divided.
        num (int): The number of segments to divide the total into.
        max_value (int | None): The maximum value any single element can have.
        min_value (int): The minimum value any single element can have. Defaults to 0.

    Returns:
        list[int]: A list of integers representing the divided segments.

    Raises:
        ValueError: If the total cannot be divided as per the given constraints.
    """
    if total < num * min_value or (max_value is not None and max_value < min_value):
        msg = "Impossible to divide under given constraints."
        raise ValueError(msg)

    if max_value is not None and num * max_value < total:
        msg = "Impossible to divide under given constraints with max_value."
        raise ValueError(msg)

    # Generate initial random segments
    segments = [random.randint(min_value, max_value or total) for _ in range(num)]
    current_total = sum(segments)

    # Adjust the segments iteratively
    while current_total != total:
        for i in range(num):
            if current_total < total and (max_value is None or segments[i] < max_value):
                increment = min(total - current_total, (max_value or total) - segments[i])
                segments[i] += increment
                current_total += increment
            elif current_total > total and segments[i] > min_value:
                decrement = min(current_total - total, segments[i] - min_value)
                segments[i] -= decrement
                current_total -= decrement

            if current_total == total:
                break

    return segments


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


async def fetch_data_from_url(url: str) -> io.BytesIO:  # pragma: no cover
    """Fetch data from a URL to be used to upload to Amazon S3."""
    async with ClientSession() as session, session.get(url) as resp:
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
    maximum = max(num, maximum)

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
    return datetime.now(UTC).replace(microsecond=0)
