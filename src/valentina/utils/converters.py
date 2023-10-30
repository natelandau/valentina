"""Converters, validators, and normalizers for Valentina."""

import re
from datetime import datetime

import aiohttp
from discord.ext import commands
from discord.ext.commands import BadArgument, Converter
from peewee import DoesNotExist, fn

from valentina.constants import (
    VALID_IMAGE_EXTENSIONS,
    CharacterConcept,
    CharClass,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.models.mongo_collections import (
    Campaign,
    Character,
    CharacterSheetSection,
    CharacterTrait,
    User,
    UserMacro,
)
from valentina.models.sqlite_models import (
    # Campaign,
    # Character,
    CustomTrait,
    Macro,
    Trait,
)
from valentina.utils import errors


class ValidChannelName(Converter):
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
    """A converter that ensures a requested character class name is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharClass:  # noqa: ARG002
        """Validate and normalize character classes."""
        try:
            return CharClass[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid character class"
            raise BadArgument(msg) from e


class ValidCharacterConcept(Converter):
    """A converter that converts a character concept name to a CharacterConcept enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharacterConcept:
        """Validate and normalize character concepts."""
        try:
            return CharacterConcept[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid character class"
            raise BadArgument(msg) from e


class ValidCharacterLevel(Converter):
    """A converter that converts a character level name to a RNGCharLevel enum."""

    async def convert(self, ctx: commands.Context, argument: str) -> RNGCharLevel:  # noqa: ARG002
        """Validate and normalize character levels."""
        try:
            return RNGCharLevel[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid character class"
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
            errors.append(
                "`Character names may only contain letters, numbers, spaces, hyphens, and underscores."
            )

        if len(errors) > 0:
            raise BadArgument("\n".join(errors))

        return re.sub(r"\s+", " ", argument).strip().title()


class ValidCharacterObject(Converter):
    """A converter that ensures a character exists."""

    async def convert(self, ctx: commands.Context, argument: str) -> Character:  # noqa: ARG002
        """Return a character object from a character id."""
        character = await Character.get(argument, fetch_links=True)
        if character:
            return character

        msg = f"No character found in database with id `{argument}`"
        raise errors.DatabaseError(msg)


class ValidCharTrait(Converter):
    """A converter that ensures a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharacterTrait:
        """Validate and normalize traits."""
        # Certain autocomplete options prefix a character id to the trait name
        match = re.match(r"(\d+)_(.*)", argument)
        if match:
            integer_part, string_part = match.groups()
            character = Character.get_by_id(int(integer_part))
            argument = string_part
        else:
            character = await ctx.bot.user_svc.fetch_active_character(ctx)

        for trait in character.traits:
            if argument.lower() == trait.name.lower():
                return trait

        msg = f"`{argument}` is not a valid trait"
        raise BadArgument(msg)


class ValidCampaign(Converter):
    """A converter to grab a campaign object from it's name."""

    async def convert(self, ctx: commands.Context, argument: str) -> Campaign:  # noqa: ARG002
        """Convert from mongo db id to campaign object."""
        campaign = await Campaign.get(argument)

        if campaign:
            return campaign

        msg = f"Campaign {argument} not found"
        raise BadArgument(msg)


class ValidClan(Converter):
    """A converter that ensures a requested vampire clan is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> VampireClan:  # noqa: ARG002
        """Validate and normalize vampire clan."""
        try:
            return VampireClan[argument]
        except KeyError as e:
            msg = f"`{argument}` is not a valid vampire clan"
            raise BadArgument(msg) from e


class ValidCustomSection(Converter):
    """Converter to ensure a custom section is valid."""

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> tuple[CharacterSheetSection, int, Character]:
        """Validate a given index.

        Returns:
            tuple[CharacterSheetSection, int, Character]: The custom section, the index, and the character
        """
        arg = int(argument)

        user_object = await User.get(ctx.user.id, fetch_links=True)  # type: ignore [attr-defined]
        active_character = await user_object.active_character(ctx.guild)
        try:
            return active_character.sheet_sections[arg], arg, active_character
        except IndexError as e:
            msg = f"`{arg}` is not a valid custom section"
            raise BadArgument(msg) from e


class ValidImageURL(Converter):
    """Converter that ensures a requested image URL is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize thumbnail URLs."""
        if not re.match(r"^https?://", argument):
            msg = "Thumbnail URLs must start with `http://` or `https://`"
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


class ValidTraitCategory(Converter):
    """A converter that ensures a requested trait category is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> TraitCategory:  # noqa: ARG002
        """Validate and normalize trait categories."""
        try:
            return TraitCategory[argument.upper()]
        except KeyError as e:
            msg = f"`{argument}` is not a valid trait category"
            raise BadArgument(msg) from e


class ValidYYYYMMDD(Converter):
    """A converter that ensures a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> datetime:  # noqa: ARG002
        """Validate and normalize traits."""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", argument):
            return datetime.strptime(argument, "%Y-%m-%d")

        msg = f"`{argument}` is not a valid trait"
        raise BadArgument(msg)


class ValidMacroFromID(Converter):
    """A converter that ensures a requested macro is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> Macro:  # noqa: ARG002
        """Convert a macro id to a Macro object."""
        try:
            return Macro.get_by_id(int(argument))
        except DoesNotExist as e:
            raise errors.DatabaseError from e


class ValidTrait(Converter):
    """A converter that ensures a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> Trait:  # noqa: ARG002
        """Validate and normalize traits."""
        for trait in Trait.select().order_by(Trait.name.asc()):
            if argument.lower() == trait.name.lower():
                return trait

        msg = f"`{argument}` is not a valid trait"
        raise BadArgument(msg)


class ValidTraitOrCustomTrait(Converter):
    """A converter to ensure a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> Trait | CustomTrait:
        """Validate and normalize traits."""
        character = await ctx.bot.user_svc.fetch_active_character(ctx)

        for trait in character.traits:
            if argument.lower() == trait.name.lower():
                return trait

        msg = f"`{argument}` is not a valid trait"
        raise BadArgument(msg)
