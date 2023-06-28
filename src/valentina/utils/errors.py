"""Custom error types for Valentina."""


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


class UserHasClaimError(Exception):
    """Raised when a user already has a claim on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "You already have a character claimed.\nUse `/unclaim` to unclaim your character."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class MacroNotFoundError(Exception):
    """Raised when a macro is not found for the user."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        macro: str | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg and macro:
            msg = f"The requested macro `{macro}` could not be found."
        elif not msg:
            msg = "The requested macro could not be found."
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


class CharacterNotFoundError(Exception):
    """Raised when a character is not found."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested character could not be found"
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class TraitNotFoundError(Exception):
    """Raised when a trait is not found on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested trait could not be found."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class SectionExistsError(Exception):
    """Raised when a section already exists on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested section already exists on the character."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)


class SectionNotFoundError(Exception):
    """Raised when a requested section is not found on a character."""

    def __init__(
        self,
        msg: str | None = None,
        e: Exception | None = None,
        *args: str | int,
        **kwargs: int | str | bool,
    ):
        if not msg:
            msg = "The requested section could not be found on the character."
        if e:
            msg += f"\nRaised from: {e.__class__.__name__}: {e}"

        super().__init__(msg, *args, **kwargs)
