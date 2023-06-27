"""Custom error types for Valentina."""


class CharacterClaimedError(Exception):
    """Raised when a character is claimed by another user."""


class UserHasClaimError(Exception):
    """Raised when a user already has a claim on a character."""


class NoClaimError(Exception):
    """Raised when a user has no claim on a character."""


class CharacterNotFoundError(Exception):
    """Raised when a character is not found."""


class TraitNotFoundError(Exception):
    """Raised when a trait is not found on a character."""


class SectionExistsError(Exception):
    """Raised when a section already exists on a character."""


class SectionNotFoundError(Exception):
    """Raised when a requested section is not found on a character."""
