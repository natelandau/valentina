"""Helpers for the webui."""

from loguru import logger
from quart import session

from valentina.models import Campaign, Character, Guild, User
from valentina.utils import ValentinaConfig, console


async def fetch_active_campaign(
    campaign_id: str = "", fetch_links: bool = False
) -> Campaign | None:
    """Fetch and return the active campaign based on the session state.

    If the guild has only one campaign, return that campaign. If there are multiple
    campaigns, return the active campaign based on the provided or existing
    `campaign_id`. Update the session with the new active campaign ID if it has changed.

    Args:
        campaign_id (str, optional): The ID of the campaign to be set as active. Defaults to "".
        fetch_links (bool, optional): Whether to fetch the database-linked objects. Defaults to False.

    Returns:
        Campaign | None: The active `Campaign` object if found, or `None` if no active campaign is determined.
    """
    if len(session["GUILD_CAMPAIGNS"]) == 0:
        return None

    if len(session["GUILD_CAMPAIGNS"]) == 1:
        return await Campaign.get(
            next(iter(session["GUILD_CAMPAIGNS"].values())), fetch_links=fetch_links
        )

    existing_campaign_id = session.get("ACTIVE_CAMPAIGN_ID", None)

    if not campaign_id:
        if existing_campaign_id:
            return await Campaign.get(existing_campaign_id, fetch_links=fetch_links)

        return None

    if existing_campaign_id == campaign_id:
        return await Campaign.get(campaign_id, fetch_links=fetch_links)

    session["ACTIVE_CAMPAIGN_ID"] = campaign_id
    return await Campaign.get(campaign_id, fetch_links=fetch_links)


async def fetch_active_character(
    character_id: str = "", fetch_links: bool = False
) -> Character | None:
    """Fetch and return the active character based on the session state.

    If the user has only one character, return that character. If there are multiple
    characters, return the active character based on the provided or existing
    `character_id`. Update the session with the new active character ID if it has changed.

    Args:
        character_id (str, optional): The ID of the character to be set as active. Defaults to "".
        fetch_links (bool, optional): Whether to fetch the database-linked objects. Defaults to False.

    Returns:
        Character | None: The active `Character` object if found, or `None` if no active character is determined.
    """
    if len(session["USER_CHARACTERS"]) == 0:
        return None

    if len(session["USER_CHARACTERS"]) == 1:
        return await Character.get(
            next(iter(session["USER_CHARACTERS"].values())), fetch_links=fetch_links
        )

    existing_character_id = session.get("ACTIVE_CHARACTER_ID", None)

    if not character_id:
        if existing_character_id:
            return await Character.get(existing_character_id, fetch_links=fetch_links)

        return None

    if existing_character_id == character_id:
        return await Character.get(character_id, fetch_links=fetch_links)

    session["ACTIVE_CHARACTER_ID"] = character_id
    return await Character.get(character_id, fetch_links=fetch_links)


async def fetch_guild(fetch_links: bool = False) -> Guild:
    """Fetch the Guild from the database based on the Discord guild_id stored in the session.

    Retrieve the guild from the database using the guild ID stored in the session,
    optionally fetching linked objects. Update the session with the guild's name
    if it has changed.

    Args:
        fetch_links (bool): Whether to fetch the database-linked objects.

    Returns:
        Guild: The Guild object corresponding to the session's guild ID.

    Raises:
        None: If the guild ID is not found in the session, the session is cleared and None is returned.
    """
    # Guard clause to prevent mangled session data
    if not session.get("GUILD_ID", None):
        session.clear()
        return None

    guild = await Guild.get(session["GUILD_ID"], fetch_links=fetch_links)

    if session.get("GUILD_NAME", None) != guild.name:
        session["GUILD_NAME"] = guild.name

    return guild


async def fetch_user(fetch_links: bool = False) -> User:
    """Fetch the User from the database based on the Discord user_id stored in the session.

    Retrieve the user from the database using the user ID stored in the session,
    optionally fetching linked objects. Update the session with the user's name
    and avatar URL if they have changed.

    Args:
        fetch_links (bool): Whether to fetch the database-linked objects.

    Returns:
        User: The User object corresponding to the session's user ID.

    Raises:
        None: If the user ID is not found in the session, the session is cleared and None is returned.
    """
    # Guard clause to prevent mangled session data
    if not session.get("USER_ID", None):
        session.clear()
        return None

    user = await User.get(session["USER_ID"], fetch_links=fetch_links)

    if session.get("USER_NAME", None) != user.name:
        logger.warning("Updating session with user name")
        session["USER_NAME"] = user.name

    if session.get("USER_AVATAR_URL", None) != user.avatar_url:
        logger.warning("Updating session with user avatar")
        session["USER_AVATAR_URL"] = user.avatar_url

    return user


async def fetch_user_characters(fetch_links: bool = True) -> list[Character]:
    """Fetch the user's characters and update the session with their names and IDs.

    Retrieve the characters owned by the user within the current guild from the database,
    optionally fetching linked objects. Update the session with a dictionary mapping
    character names to their IDs if the session data has changed.

    Args:
        fetch_links (bool): Whether to fetch the database-linked objects.

    Returns:
        list[Character]: A list of characters owned by the user within the current guild.

    Raises:
        None: If the user ID or guild ID is not found in the session, the session is cleared and an empty list is returned.
    """
    # Guard clause to prevent mangled session data
    if not session.get("USER_ID", None) or not session.get("GUILD_ID", None):
        session.clear()
        return []

    characters = await Character.find(
        Character.user_owner == session["USER_ID"],
        Character.guild == session["GUILD_ID"],
        Character.type_player == True,  # noqa: E712
        fetch_links=fetch_links,
    ).to_list()

    character_dict = dict(sorted({x.name: str(x.id) for x in characters}.items()))
    if session.get("USER_CHARACTERS", None) != character_dict:
        logger.warning("Updating session with characters")
        session["USER_CHARACTERS"] = character_dict

    return characters


async def fetch_campaigns(fetch_links: bool = True) -> list[Campaign]:
    """Fetch the guild's campaigns and update the session with their names and IDs.

    Retrieve the campaigns associated with the current guild from the database,
    optionally fetching linked objects. Update the session with a dictionary
    mapping campaign names to their IDs if the session data has changed.

    Args:
        fetch_links (bool): Whether to fetch the database-linked objects.

    Returns:
        list[Campaign]: A list of campaigns associated with the guild.

    Raises:
        None: If the guild ID is not found in the session, the session is cleared and an empty list is returned.
    """
    # Guard clause to prevent mangled session data
    if not session.get("GUILD_ID", None):
        session.clear()
        return []

    campaigns = await Campaign.find(
        Campaign.guild == session["GUILD_ID"],
        Campaign.is_deleted == False,  # noqa: E712
        fetch_links=fetch_links,
    ).to_list()

    campaigns_dict = dict(sorted({x.name: str(x.id) for x in campaigns}.items()))
    if session.get("GUILD_CAMPAIGNS", None) != campaigns_dict:
        logger.warning("Updating session with campaigns")
        session["GUILD_CAMPAIGNS"] = campaigns_dict

    return campaigns


async def update_session() -> None:
    """Update the session with the user's current state.

    Fetch and update session data related to the user's guild, user details,
    characters, and campaigns. If the application is in debug mode and the
    log level is set to "DEBUG" or "TRACE", log the session details to the console.

    Returns:
        None
    """
    logger.debug("Updating session")
    await fetch_guild(fetch_links=False)
    await fetch_user(fetch_links=False)
    await fetch_user_characters(fetch_links=False)
    await fetch_campaigns(fetch_links=False)

    if ValentinaConfig().webui_debug and ValentinaConfig().webui_log_level.upper() in [
        "DEBUG",
        "TRACE",
    ]:
        console.rule("Session")
        for key, value in session.items():
            console.log(f"{key}={value}")
        console.rule()
