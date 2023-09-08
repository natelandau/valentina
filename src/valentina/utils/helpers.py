"""Helper functions for Valentina."""
import io
import random
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import aiohttp
import discord
from aiohttp import ClientSession

from valentina.constants import (
    CLAN_DISCIPLINES,
    DICEROLL_THUBMS,
    ChannelPermission,
    MaxTraitValue,
    RollResultType,
    XPMultiplier,
    XPNew,
)
from valentina.utils import errors

from .errors import BotMissingPermissionsError


async def assert_permissions(ctx: discord.ApplicationContext, **permissions: bool) -> None:
    """Check if the bot has the required permissions to run the command.""."""
    if missing := [
        perm for perm, value in permissions.items() if getattr(ctx.app_permissions, perm) != value
    ]:
        raise BotMissingPermissionsError(missing)


def changelog_parser(
    changelog: str, last_posted_version: str
) -> dict[str, dict[str, str | list[str]]]:
    """Parse a changelog to extract versions, dates, features, and fixes, stopping at the last posted version.

    The function looks for sections in the changelog that correspond to version numbers,
    feature and fix descriptions. It ignores specified sections like Docs, Refactor, Style, and Test.

    Args:
        changelog (str): The changelog text to parse.
        last_posted_version (str): The last version that was posted, parsing stops when this version is reached.

    Returns:
        Dict[str, dict[str, str | list[str]]]: A dictionary containing the parsed data.
        The key is the version number, and the value is another dictionary with date, features, and fixes.
    """
    # Precompile regex patterns
    version = re.compile(r"## v(\d+\.\d+\.\d+)")
    date = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")
    feature = re.compile(r"### Feat", re.I)
    fix = re.compile(r"### Fix", re.I)
    ignored_sections = re.compile(r"### (docs|refactor|style|test|perf|ci|build|chore)", re.I)

    # Initialize dictionary to store parsed data
    changes: dict[str, dict[str, str | list[str]]] = {}
    in_features = in_fixes = False  # Flags for parsing feature and fix sections

    # Split changelog into lines and iterate
    for line in changelog.split("\n"):
        # Skip empty lines
        if line == "":
            continue

        # Skip lines with ignored section headers
        if ignored_sections.match(line):
            in_features = in_fixes = False
            continue

        # Version section
        if version_match := version.match(line):
            version_number = version_match.group(1)
            if version_number == last_posted_version:
                break  # Stop parsing when last posted version is reached

            changes[version_number] = {
                "date": date.search(line).group(1),
                "features": [],
                "fixes": [],
            }
            continue

        if bool(feature.match(line)):
            in_features = True
            in_fixes = False
            continue

        if bool(fix.match(line)):
            in_features = False
            in_fixes = True
            continue

        line = re.sub(r" \(#\d+\)$", "", line)  # noqa: PLW2901
        line = re.sub(r"(\*\*)", "", line)  # noqa: PLW2901
        if in_features:
            changes[version_number]["features"].append(line)  # type: ignore [union-attr]
        if in_fixes:
            changes[version_number]["fixes"].append(line)  # type: ignore [union-attr]

    return changes


def diceroll_thumbnail(ctx: discord.ApplicationContext, result: RollResultType) -> str:
    """Take a string and return a random gif url.

    Args:
        ctx (discord.ApplicationContext): The application context.
        result (RollResultType): The roll result type.

    Returns:
    Optional[str]: The thumbnail URL, or None if no thumbnail is found.
    """
    # Get the list of default thumbnails for the result type
    thumb_list = DICEROLL_THUBMS.get(result.name, [])

    # Get the list of thumbnails from the database
    database_thumbs = ctx.bot.guild_svc.fetch_roll_result_thumbs(ctx)  # type: ignore [attr-defined]

    # Find the matching category in the database thumbnails (case insensitive)
    matching_category = next(
        (category for category in database_thumbs if category.lower() == result.name.lower()), None
    )

    # If a matching category was found, extend the list of thumbnails with the database thumbnails
    if matching_category:
        thumb_list.extend(database_thumbs[matching_category])

    # If there are no thumbnails, return None
    if not thumb_list:
        return None

    # Return a random thumbnail
    return random.choice(thumb_list)


def fetch_clan_disciplines(clan: str) -> list[str]:
    """Fetch the disciplines for a clan.

    Examples:
        >>> fetch_clan_disciplines("toreador")
        ['Auspex', 'Celerity', 'Presence']


    """
    return CLAN_DISCIPLINES[clan.title()]


async def fetch_random_name(gender: str | None = None, country: str = "us") -> tuple[str, str]:
    """Fetch a random name from the randomuser.me API."""
    if not gender:
        gender = random.choice(["male", "female"])

    params = {"gender": gender, "nat": country, "inc": "name"}
    url = f"https://randomuser.me/api/?{urlencode(params)}"
    async with ClientSession() as session, session.get(url) as res:
        if 300 > res.status >= 200:  # noqa: PLR2004
            data = await res.json()
            return (data["results"][0]["name"]["first"], data["results"][0]["name"]["last"])

    return ("John", "Doe")


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


async def fetch_data_from_url(url: str) -> io.BytesIO:
    """Fetch data from a URL to be used to upload to Amazon S3."""
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        if resp.status != 200:  # noqa: PLR2004
            raise errors.URLNotAvailableError(f"Could not fetch data from {url}")

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


def round_trait_value(value: int, max_value: int) -> int:
    """Bound a value to a trait value.

    Args:
        value (int): The value to bound.
        max_value (int): The maximum value.

    Returns:
        int: The bounded value.

    >>> round_trait_value(5, 5)
    5

    >>> round_trait_value(6, 5)
    5

    >>> round_trait_value(-10, 5)
    0
    """
    if value < 0:
        return 0
    if value > max_value:
        return max_value

    return value


def set_channel_perms(requested_permission: ChannelPermission) -> discord.PermissionOverwrite:
    """Translate a ChannelPermission enum to a discord.PermissionOverwrite object.

    Takes a requested channel permission represented as an enum and
    sets the properties of a discord.PermissionOverwrite object
    to match those permissions.

    Args:
        requested_permission (ChannelPermission): The channel permission enum.

    Returns:
        discord.PermissionOverwrite: Permission settings as a Discord object.
    """
    # Map each ChannelPermission to the properties that should be False
    permission_mapping: dict[ChannelPermission, dict[str, bool]] = {
        ChannelPermission.HIDDEN: {
            "add_reactions": False,
            "manage_messages": False,
            "read_messages": False,
            "send_messages": False,
            "view_channel": False,
            "read_message_history": False,
        },
        ChannelPermission.READ_ONLY: {
            "add_reactions": True,
            "manage_messages": False,
            "read_messages": True,
            "send_messages": False,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": False,
        },
        ChannelPermission.POST: {
            "add_reactions": True,
            "manage_messages": False,
            "read_messages": True,
            "send_messages": True,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": True,
        },
        ChannelPermission.MANAGE: {
            "add_reactions": True,
            "manage_messages": True,
            "read_messages": True,
            "send_messages": True,
            "view_channel": True,
            "read_message_history": True,
            "use_slash_commands": True,
        },
    }

    # Create a permission overwrite object
    perms = discord.PermissionOverwrite()
    # Update the permission overwrite object based on the enum
    for key, value in permission_mapping.get(requested_permission, {}).items():
        setattr(perms, key, value)

    return perms


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
