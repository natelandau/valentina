"""Conftest for tests/webui."""

import random
import string
from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest
from quart.typing import TestClientProtocol

from tests.factories import *
from valentina.models import Campaign, Character, Guild
from valentina.utils import console
from valentina.webui import create_app
from valentina.webui.utils.helpers import CharacterSessionObject


@pytest.fixture
async def test_client() -> AsyncGenerator[TestClientProtocol, None]:
    """Returns a test client for the Valentina web interface."""
    app = create_app("Testing")
    async with app.test_client() as client:
        yield client


@pytest.fixture
def mock_session() -> Callable[[], dict[str, Any]]:
    """Create a mock session for testing."""

    def _inner(
        authorized: bool = True,
        characters: list[Character] = [],
        campaigns: list[Campaign] = [],
        active_character: Character | str = None,
        active_campaign: Campaign | str = None,
        is_storyteller: bool = False,
        user_name: str = "test_user",
        guild_name: str = "test_guild",
        user_id: str = "1234567890",
        guild_id: str = "0987654321",
    ) -> dict:
        """Inner function to allow using arguments."""
        # Common session data
        mock_session: dict[str, Any] = {
            "DISCORD_USER_ID": user_id,
            "GUILD_ID": guild_id,
            "GUILD_NAME": guild_name,
            "USER_AVATAR_URL": f"https://cdn.discordapp.com/avatars/{random.randint(100000000000000, 999999999999999)}/{random.randint(100000000000000, 999999999999999)}.png?size=1024",
            "USER_ID": user_id,
            "USER_NAME": user_name,
            "IS_STORYTELLER": False,
        }

        if authorized:
            mock_session.update(
                {
                    "DISCORD_OAUTH2_STATE": f"{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(106))}.{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(35))}--{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))}",
                    "DISCORD_OAUTH2_TOKEN": {
                        "token_type": "Bearer",
                        "access_token": "".join(
                            random.choice(string.ascii_letters + string.digits) for _ in range(32)
                        ),
                        "expires_in": 604800,
                        "refresh_token": "".join(
                            random.choice(string.ascii_letters + string.digits) for _ in range(32)
                        ),
                        "scope": ["identify", "email", "connections", "guilds.join", "guilds"],
                        "expires_at": 2543075477.311455,
                    },
                }
            )

        mock_session["ALL_CHARACTERS"] = [
            CharacterSessionObject(
                id=str(x.id),
                name=x.name,
                campaign_name="mock campaign name",
                campaign_id=x.campaign,
                owner_name="mock owner name",
                owner_id=x.user_owner,
            ).__dict__
            for x in characters
        ]

        mock_session["USER_CHARACTERS"] = [
            CharacterSessionObject(
                id=str(x.id),
                name=x.name,
                campaign_name="mock campaign name",
                campaign_id=x.campaign,
                owner_name="mock owner name",
                owner_id=x.user_owner,
            ).__dict__
            for x in characters
        ]

        mock_session["STORYTELLER_CHARACTERS"] = [
            CharacterSessionObject(
                id=str(x.id),
                name=x.name,
                campaign_name="mock campaign name",
                campaign_id=x.campaign,
                owner_name="mock owner name",
                owner_id=x.user_owner,
            ).__dict__
            for x in characters
        ]

        mock_session["GUILD_CAMPAIGNS"] = {c.name: str(c.id) for c in campaigns}

        if active_character:
            mock_session["ACTIVE_CHARACTER_ID"] = (
                str(active_character.id)
                if isinstance(active_character, Character)
                else active_character
            )
        else:
            mock_session["ACTIVE_CHARACTER_ID"] = str(characters[0].id) if characters else ""

        if active_campaign:
            mock_session["ACTIVE_CAMPAIGN_ID"] = (
                str(active_campaign.id)
                if isinstance(active_campaign, Campaign)
                else active_campaign
            )
        else:
            mock_session["ACTIVE_CAMPAIGN_ID"] = str(campaigns[0].id) if campaigns else ""

        mock_session["IS_STORYTELLER"] = is_storyteller

        return mock_session

    return _inner
