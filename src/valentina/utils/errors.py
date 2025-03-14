"""Custom error types for Valentina."""

from discord import DiscordException


class VersionNotFoundError(Exception):
    """Raised when we can't find a version in the changelog."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Version not found in changelog."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class MissingConfigurationError(Exception):
    """Raised when a configuration variable is missing."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "A configuration variable is missing."
        else:
            msg = f"A configuration variable is missing: {msg}"

        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class BotMissingPermissionsError(DiscordException):
    """Raised when the bot is missing permissions to run a command."""

    def __init__(self, permissions: list[str]) -> None:
        missing = [
            f"**{perm.replace('_', ' ').replace('guild', 'server').title()}**"
            for perm in permissions
        ]
        sub = f"{', '.join(missing[:-1])} and {missing[-1]}" if len(missing) > 1 else missing[0]
        super().__init__(f"I require {sub} permissions to run this command.")


class ChannelTypeError(Exception):
    """Raised when a channel is not the correct type."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "This channel is not the correct type."
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


class NoCharacterClassError(Exception):
    """Raised when a character's class is not a valid CharClass enum value."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The character class is not valid."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NoExperienceInCampaignError(Exception):
    """Raised when a no experience is found for a campaign."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "This user has no experience in this campaign."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NotEnoughFreebiePointsError(Exception):
    """Raised when there are not enough freebie points to upgrade a trait."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Not enough freebie points to upgrade trait."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class TraitAtMinValueError(Exception):
    """Raised when a user tries to update a trait can not be lowered below 0."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Trait can not be lowered below 0"
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class TraitAtMaxValueError(Exception):
    """Raised when a user tries to update a trait already at max value."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Trait is already at max value."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class NotEnoughExperienceError(DiscordException):
    """Raised when a user does not have enough experience to perform an action."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "Not enough experience to perform this action."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class S3ObjectExistsError(Exception):
    """Raised when an S3 object already exists."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "A file with that name already exists."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class ServiceDisabledError(DiscordException):
    """Raised when a service is disabled."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested service is disabled"
        else:
            msg = f"The requested service is disabled: {msg}"

        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class TraitExistsError(DiscordException):
    """Raised when adding a trait that already exists on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "This trait already exists on this character."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class URLNotAvailableError(DiscordException):
    """Raised when a URL is not available."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested URL is not available."
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


class NoCTXError(Exception):
    """Raised when the context was not passed."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The context object was not passed."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)
