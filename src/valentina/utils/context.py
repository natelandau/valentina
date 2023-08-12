"""Custom context for Valentina. This is a subclass of discord.py's ApplicationContext which adds some utility functions."""

from discord import ApplicationContext

from .errors import BotMissingPermissionsError


class Context(ApplicationContext):
    """Custom context for Valentina."""

    async def assert_permissions(self, **permissions: bool) -> None:
        """Check if the bot has the required permissions to run the command.""."""
        if missing := [
            perm
            for perm, value in permissions.items()
            if getattr(self.app_permissions, perm) != value
        ]:
            raise BotMissingPermissionsError(missing)
