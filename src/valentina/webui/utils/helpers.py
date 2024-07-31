"""Helpers for the webui."""

from loguru import logger
from quart.sessions import SessionMixin

from valentina.models import Campaign, Character, Guild, User


async def fetch_active_campaign(
    session: SessionMixin, campaign_id: str = "", fetch_links: bool = False
) -> Campaign | None:
    """Update and return the active campaign from the session."""
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
    session.modified = True
    return await Campaign.get(campaign_id, fetch_links=fetch_links)


async def fetch_active_character(
    session: SessionMixin, character_id: str = "", fetch_links: bool = False
) -> Character | None:
    """Update and return the active character from the session."""
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
    session.modified = True
    return await Character.get(character_id, fetch_links=fetch_links)


async def fetch_guild(session: SessionMixin, fetch_links: bool = True) -> Guild:
    """Fetch the database Guild based on Discord guild_id from the session. Updates the session with the guild name.

    Args:
        session (SessionMixin): The session to fetch the guild from.
        fetch_links (bool): Whether to fetch the database linked objects.
    """
    # Guard clause to prevent mangled session data
    if not session.get("GUILD_ID", None):
        session.clear()
        return None

    guild = await Guild.get(session["GUILD_ID"], fetch_links=fetch_links)

    if session.get("GUILD_NAME", None) != guild.name:
        session["GUILD_NAME"] = guild.name
        session.modified = True

    return guild


async def fetch_user(session: SessionMixin, fetch_links: bool = True) -> User:
    """Fetch the database User based on Discord user_id from the session.

    Args:
        fetch_links (bool): Whether to fetch the database linked objects.
        session (SessionMixin): The session to fetch the user from.
    """
    # Guard clause to prevent mangled session data
    if not session.get("USER_ID", None):
        session.clear()
        return None

    user = await User.get(session["USER_ID"], fetch_links=fetch_links)

    if session.get("USER_NAME", None) != user.name:
        logger.warning("Updating session with user name")
        session["USER_NAME"] = user.name
        session.modified = True

    if session.get("USER_AVATAR_URL", None) != user.avatar_url:
        logger.warning("Updating session with user avatar")
        session["USER_AVATAR_URL"] = user.avatar_url
        session.modified = True

    return user


async def fetch_user_characters(session: SessionMixin, fetch_links: bool = True) -> list[Character]:
    """Fetch the user's characters and return them as a list. Updates the session with a dictionary of character names and ids.

    Args:
        fetch_links (bool): Whether to fetch the database linked objects.
        session (SessionMixin): The session to fetch the characters from.
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
        session.modified = True

    return characters


async def fetch_campaigns(session: SessionMixin, fetch_links: bool = True) -> list[Campaign]:
    """Fetch the guild's campaign and return them as a list. Updates the session with a dictionary of campaign names and ids.

    Args:
        fetch_links (bool): Whether to fetch the database linked objects.
        session (SessionMixin): The session to fetch the characters from.
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
        session.modified = True

    return campaigns


async def update_session(session: SessionMixin) -> None:
    """Make updates to the session based on the user's current state.

    Args:
        session (SessionMixin): The session to update.
    """
    logger.debug("Updating session")
    await fetch_guild(session, fetch_links=False)
    await fetch_user(session, fetch_links=False)
    await fetch_user_characters(session, fetch_links=False)
    await fetch_campaigns(session, fetch_links=False)
