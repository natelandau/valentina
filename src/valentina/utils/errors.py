"""Custom error types for Valentina."""


class CharacterClaimedError(Exception):
    """Raised when a character is claimed by another user."""


class UserHasClaimError(Exception):
    """Raised when a user already has a claim on a character."""


class NoClaimError(Exception):
    """Raised when a user has no claim on a character."""
