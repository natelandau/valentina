"""Converters, validators, and normalizers for Valentina."""

import re
from datetime import UTC, datetime

import aiohttp
from discord.ext import commands
from discord.ext.commands import BadArgument, Converter

from valentina.constants import (
    VALID_IMAGE_EXTENSIONS,
    CharacterConcept,
    CharClass,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.discord.utils import fetch_channel_object
from valentina.models import (
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    Character,
    CharacterTrait,
    InventoryItem,
    Note,
)


class ValidCampaign(Converter):
    """Convert a campaign name to a Campaign object.

    This converter takes a campaign name as input and retrieves the corresponding
    Campaign object from the database. It ensures that the provided name
    corresponds to a valid, existing campaign. If the campaign is not found,
    raise a BadArgument exception.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> Campaign:  # noqa: ARG002
        """Convert a MongoDB ID to a Campaign object.

        Retrieve a Campaign object from the database using the provided MongoDB ID.
        If a matching campaign is found, return the Campaign object. Otherwise,
        raise a BadArgument exception with an appropriate error message.

        Args:
            ctx (commands.Context): The context of the command invocation.
            argument (str): The MongoDB ID of the campaign to retrieve.

        Returns:
            Campaign: The retrieved Campaign object.

        Raises:
            BadArgument: If no campaign is found with the given ID.
        """
        campaign = await Campaign.get(argument, fetch_links=True)

        if campaign:
            return campaign

        msg = f"Campaign {argument} not found"
        raise BadArgument(msg)


class ValidCampaignBook(Converter):  # pragma: no cover
    """Convert a book ID to a CampaignBook object."""

    async def convert(self, ctx: commands.Context, argument: str) -> CampaignBook:  # noqa: ARG002
        """Convert a book ID to a CampaignBook object.

        Args:
            ctx: The context of the command invocation.
            argument: The book ID to convert.

        Returns:
            CampaignBook: The retrieved CampaignBook object.

        Raises:
            BadArgument: If no book is found with the given ID.
        """
        book = await CampaignBook.get(argument)
        if book:
            return book

        msg = f"`{argument}` is not a valid book"
        raise BadArgument(msg)


class ValidCampaignBookChapter(Converter):  # pragma: no cover
    """Convert a chapter ID to a CampaignBookChapter object."""

    async def convert(self, ctx: commands.Context, argument: str) -> CampaignBookChapter:  # noqa: ARG002
        """Convert a chapter ID to a CampaignBookChapter object.

        Args:
            ctx: The context of the command invocation.
            argument: The chapter ID to convert.

        Returns:
            CampaignBookChapter: The retrieved CampaignBookChapter object.

        Raises:
            BadArgument: If no chapter is found with the given ID.
        """
        chapter = await CampaignBookChapter.get(argument)
        if chapter:
            return chapter

        msg = f"`{argument}` is not a valid chapter"
        raise BadArgument(msg)


class ValidBookNumber(Converter):
    """Convert and validate a book number for an active campaign."""

    async def convert(self, ctx: commands.Context, argument: str) -> int:
        """Convert and validate a book number for an active campaign.

        Args:
            ctx: The context of the command invocation.
            argument: The book number to convert and validate.

        Returns:
            int: The validated book number.

        Raises:
            BadArgument: If no active campaign is found, the argument is not a valid integer,
                         the book number is less than 1, or the book number is not part of the active campaign.
        """
        channel_objects = await fetch_channel_object(ctx, raise_error=False)
        campaign = channel_objects.campaign

        if not campaign:
            msg = "No active campaign found in this channel"
            raise BadArgument(msg)

        campaign_book_numbers = [x.number for x in await campaign.fetch_books()]

        try:
            book_number = int(argument)
        except ValueError as e:
            msg = f"`{argument}` is not a valid chapter number"
            raise BadArgument(msg) from e

        if book_number < 1:
            msg = "Chapter numbers must be greater than 0"
            raise BadArgument(msg)

        if book_number not in campaign_book_numbers:
            msg = f"Requested book number `{book_number}` is not part of the active campaign."
            raise BadArgument(msg)

        return book_number


class ValidChapterNumber(Converter):
    """Convert and validate a chapter number for a book."""

    async def convert(self, ctx: commands.Context, argument: str) -> int:
        """Convert and validate a chapter number for a book.

        Args:
            ctx: The context of the command invocation.
            argument: The chapter number to convert and validate.

        Returns:
            int: The validated chapter number.

        Raises:
            BadArgument: If the argument is not a valid integer, the chapter number is less than 1,
                         or the chapter number is not part of the book.
        """
        channel_objects = await fetch_channel_object(ctx, raise_error=False)
        book = channel_objects.book
        book_chapter_numbers = [x.number for x in await book.fetch_chapters()]

        try:
            chapter_number = int(argument)
        except ValueError as e:
            msg = f"`{argument}` is not a valid chapter number"
            raise BadArgument(msg) from e

        if chapter_number < 1:
            msg = "Chapter numbers must be greater than 0"
            raise BadArgument(msg)

        if chapter_number not in book_chapter_numbers:
            msg = f"Requested chapter number `{chapter_number}` is not part of the book."
            raise BadArgument(msg)

        return chapter_number


class ValidChannelName(Converter):  # pragma: no cover
    """A converter that ensures a requested channel name is valid."""

    ALLOWED_CHARACTERS = r"ABCDEFGHIJKLMNOPQRSTUVWXYZ!?'`-<>\/"
    TRANSLATED_CHARACTERS = "𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹ǃ？’’-＜＞⧹⧸"  # noqa: RUF001

    @classmethod
    def translate_name(cls, name: str, *, from_unicode: bool = True) -> str:
        """Translates `name` into a format that is allowed in discord channel names.

        If `from_unicode` is True, the name is translated from a discord-safe format, back to normalized text.
        """
        if from_unicode:
            table = str.maketrans(cls.ALLOWED_CHARACTERS, cls.TRANSLATED_CHARACTERS)
        else:
            table = str.maketrans(cls.TRANSLATED_CHARACTERS, cls.ALLOWED_CHARACTERS)

        return name.translate(table)

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # noqa: ARG002
        """Attempt to replace any invalid characters with their approximate Unicode equivalent."""
        # Chain multiple words to a single one
        argument = argument.replace("_", "-").replace(" ", "-")

        min_channel_length = 2
        max_channel_length = 96
        if not (min_channel_length <= len(argument) <= max_channel_length):
            msg = "Channel name must be between 2 and 96 chars long"
            raise BadArgument(msg)

        if not all(c.isalnum() or c in self.ALLOWED_CHARACTERS for c in argument):
            msg = "Channel name must only consist of alphanumeric characters, minus signs or apostrophes."
            raise BadArgument(msg)

        # Replace invalid characters with unicode alternatives.
        return argument


class ValidCharClass(Converter):
    """Convert a CharClass name to a CharClass enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharClass:  # noqa: ARG002
        """Validate and normalize character classes."""
        try:
            return CharClass[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid character class"
            raise BadArgument(msg) from e


class ValidCharacterConcept(Converter):
    """Convert a CharacterConcept name to a CharacterConcept enum."""

    async def convert(
        self,
        ctx: commands.Context,  # noqa: ARG002
        argument: str,
    ) -> CharacterConcept:
        """Validate and normalize character concepts."""
        try:
            return CharacterConcept[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid character class"
            raise BadArgument(msg) from e


class ValidCharacterLevel(Converter):
    """Convert a RNGCharLevel name to a RNGCharLevel enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> RNGCharLevel:  # noqa: ARG002
        """Validate and normalize character levels."""
        try:
            return RNGCharLevel[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid rng character level"
            raise BadArgument(msg) from e


class ValidCharacterName(Converter):
    """A converter that ensures character names are valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize character names."""
        errors = []
        max_len = 30

        if (name_len := len(argument)) > max_len:
            errors.append(f"`{argument}` is too long by {name_len - max_len} characters.")

        if not re.match(r"^[a-zA-Z0-9àèìòñùçëïüÁÉÖÜÑ_ -]+$", argument):
            errors.append(  # type: ignore [unreachable]
                "`Character names may only contain letters, numbers, spaces, hyphens, and underscores.",
            )

        if len(errors) > 0:
            raise BadArgument("\n".join(errors))

        return re.sub(r"\s+", " ", argument).strip().title()


class ValidCharacterObject(Converter):
    """A converter that returns a Character object from the database.from it's id."""

    async def convert(self, ctx: commands.Context, argument: str) -> Character:  # noqa: ARG002
        """Return a character object from a character id."""
        character = await Character.get(argument, fetch_links=True)
        if character:
            return character

        msg = f"No character found in database with id `{argument}`"
        raise BadArgument(msg)


class ValidCharTrait(Converter):
    """A converter that converts a CharacterTrait id to a CharacterTrait object."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharacterTrait:  # noqa: ARG002
        """Validate and normalize traits."""
        trait = await CharacterTrait.get(argument)
        if trait:
            return trait

        msg = f"`{argument}` is not a valid trait"
        raise BadArgument(msg)


class ValidClan(Converter):
    """Converter a VampireClan name to a VampireClan enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> VampireClan:  # noqa: ARG002
        """Validate and normalize vampire clan."""
        try:
            return VampireClan[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid vampire clan"
            raise BadArgument(msg) from e


class ValidImageURL(Converter):  # pragma: no cover
    """Converter that ensures a requested image URL is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize thumbnail URLs."""
        if not re.match(r"^https?://", argument):
            msg = "Thumbnail URLs must start with `http://` or `https://`"  # type: ignore [unreachable]
            raise BadArgument(msg)

        # Extract the file extension from the URL
        file_extension = argument.split(".")[-1].lower()

        if file_extension not in VALID_IMAGE_EXTENSIONS:
            msg = f"Thumbnail URLs must end with a valid image extension: {', '.join(VALID_IMAGE_EXTENSIONS)}"
            raise BadArgument(msg)

        async with aiohttp.ClientSession() as session, session.get(argument) as r:
            success_status_codes = [200, 201, 202, 203, 204, 205, 206]
            if r.status not in success_status_codes:
                msg = f"Thumbnail URL could not be accessed\nStatus: {r.status}"
                raise BadArgument(msg)

        # Replace media.giphy.com URLs with i.giphy.com URLs
        return re.sub(r"//media\.giphy\.com", "//i.giphy.com", argument)


class ValidNote(Converter):  # pragma: no cover
    """A converter that returns a Note object from the database.from it's id."""

    async def convert(self, ctx: commands.Context, argument: str) -> Note:  # noqa: ARG002
        """Return a note object from a note id."""
        note = await Note.get(argument)
        if note:
            return note

        msg = f"No note found with id `{argument}`"
        raise BadArgument(msg)


class ValidTraitCategory(Converter):
    """Convert a TraitCategory name to a TraitCategory enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> TraitCategory:  # noqa: ARG002
        """Validate and normalize trait categories."""
        try:
            return TraitCategory[argument.upper()]
        except KeyError as e:
            msg = f"`{argument}` is not a valid trait category"
            raise BadArgument(msg) from e


class ValidInventoryItemFromID(Converter):  # pragma: no cover
    """Convert a InventoryItem name to a InventoryItem enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> InventoryItem:  # noqa: ARG002
        """Validate and return a InventoryItem from it's id."""
        try:
            return await InventoryItem.get(argument)
        except KeyError as e:
            msg = f"`{argument}` is not an existing InventoryItem id"
            raise BadArgument(msg) from e


class ValidTraitFromID(Converter):  # pragma: no cover
    """Convert a TraitCategory name to a TraitCategory enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharacterTrait:  # noqa: ARG002
        """Validate and return a CharacterTrait from it's id."""
        try:
            return await CharacterTrait.get(argument)
        except KeyError as e:
            msg = f"`{argument}` is not an existing trait id"
            raise BadArgument(msg) from e


class ValidYYYYMMDD(Converter):
    """Convert a string in the form of YYYY-MM-DD to a datetime object."""

    async def convert(self, ctx: commands.Context, argument: str) -> datetime:  # noqa: ARG002
        """Validate and normalize traits."""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", argument):
            return datetime.strptime(argument, "%Y-%m-%d").replace(tzinfo=UTC)

        msg = f"`{argument}` is not a valid trait"  # type: ignore [unreachable]
        raise BadArgument(msg)
