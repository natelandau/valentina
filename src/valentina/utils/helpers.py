"""Helper functions for Valentina."""
import random
from datetime import datetime, timezone
from urllib.parse import urlencode

import discord
from aiohttp import ClientSession

from valentina.models.constants import (
    CLAN_DISCIPLINES,
    DICEROLL_THUBMS,
    ChannelPermission,
    MaxTraitValue,
    RollResultType,
    XPMultiplier,
    XPNew,
)

from .errors import BotMissingPermissionsError


async def assert_permissions(ctx: discord.ApplicationContext, **permissions: bool) -> None:
    """Check if the bot has the required permissions to run the command.""."""
    if missing := [
        perm for perm, value in permissions.items() if getattr(ctx.app_permissions, perm) != value
    ]:
        raise BotMissingPermissionsError(missing)


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


def set_channel_perms(requested_permission: ChannelPermission) -> discord.PermissionOverwrite:
    """Set the channel permissions for a role from a ChannelPermission enum.

    Args:
        requested_permission (ChannelPermission): The requested channel permission.

    Returns:
        discord.PermissionOverwrite: The corresponding Discord permission overwrite.
    """
    perms = discord.PermissionOverwrite()

    match requested_permission:
        case ChannelPermission.HIDDEN:
            perms.send_messages = False  # type: ignore [misc]
            perms.read_messages = False  # type: ignore [misc]
            perms.manage_messages = False  # type: ignore [misc]
            perms.add_reactions = False  # type: ignore [misc]
            perms.view_channel = False  # type: ignore [misc]

        case ChannelPermission.READ_ONLY:
            perms.send_messages = False  # type: ignore [misc]
            perms.read_messages = True  # type: ignore [misc]
            perms.manage_messages = False  # type: ignore [misc]
            perms.add_reactions = True  # type: ignore [misc]
            perms.view_channel = True  # type: ignore [misc]

        case ChannelPermission.POST:
            perms.send_messages = True  # type: ignore [misc]
            perms.read_messages = True  # type: ignore [misc]
            perms.manage_messages = False  # type: ignore [misc]
            perms.add_reactions = True  # type: ignore [misc]
            perms.view_channel = True  # type: ignore [misc]

        case ChannelPermission.MANAGE:
            perms.send_messages = True  # type: ignore [misc]
            perms.read_messages = True  # type: ignore [misc]
            perms.manage_messages = True  # type: ignore [misc]
            perms.add_reactions = True  # type: ignore [misc]
            perms.view_channel = True  # type: ignore [misc]

    return perms


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


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)
