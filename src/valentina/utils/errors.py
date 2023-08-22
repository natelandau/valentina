"""Custom error types for Valentina."""
from discord import DiscordException


class BotMissingPermissionsError(DiscordException):
    """Raised when the bot is missing permissions to run a command."""

    def __init__(self, permissions: list[str]) -> None:
        missing = [
            f"**{perm.replace('_', ' ').replace('guild', 'server').title()}**"
            for perm in permissions
        ]
        sub = f"{', '.join(missing[:-1])} and {missing[-1]}" if len(missing) > 1 else missing[0]
        super().__init__(f"I require {sub} permissions to run this command.")


class CharacterClaimedError(Exception):
    """Raised when a character is claimed by another user."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested character is already claimed by another user."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class DatabaseError(Exception):
    """Raised when a database error occurs or when items are not found."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "A database error occurred, the requested item may not exist"
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class MessageTooLongError(Exception):
    """Raised when a message is too long to send."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Apologies. The message was too long to send. This bug has been reported."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NoActiveCampaignError(Exception):
    """Raised when a no active campaign is found."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "No active campaign found\nUse `/campaign set_active`"
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NoClaimError(Exception):
    """Raised when a user has no claim on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "You have no character claimed.\nUse `/claim` to claim a character."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NoMatchingItemsError(Exception):
    """Raised when no matching items are found in the database."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "No matching records were found in the database."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class ValidationError(Exception):
    """Raised when a validation error occurs."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "A validation error occurred."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)
