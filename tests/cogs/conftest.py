# type: ignore
"""Shared fixtures for testing cogs."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _mock_confirm_action(mocker) -> None:
    """Fixture for mocking the confirm_action function within cogs.  This fixture automatically confirms the action."""
    for cog in ("experience", "characters", "campaign", "storyteller"):
        mocker.patch(
            f"valentina.discord.cogs.{cog}.confirm_action",
            AsyncMock(
                return_value=(True, AsyncMock(), AsyncMock()),
            ),
        )
