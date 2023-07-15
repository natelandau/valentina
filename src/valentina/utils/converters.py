"""Converters, validators, and normalizers for Valentina."""


import re

import aiohttp
from discord.ext.commands import BadArgument, Context, Converter

from valentina.models.constants import DBConstants
from valentina.models.database import Character, CharacterClass, TraitCategory, VampireClan
from valentina.utils.errors import CharacterNotFoundError


class ValidCharacterClass(Converter):
    """A converter that ensures a requested character class name is valid."""

    async def convert(self, ctx: Context, argument: str) -> CharacterClass:  # noqa: ARG002
        """Validate and normalize character classes."""
        for c in DBConstants.char_classes():
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid character class")


class ValidCharacterName(Converter):
    """A converter that ensures character names are valid."""

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
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

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        """Attempt to replace any invalid characters with their approximate Unicode equivalent."""
        # Chain multiple words to a single one
        argument = argument.replace("_", "-").replace(" ", "-")

        min_channel_length = 2
        max_channel_length = 96
        if not (min_channel_length <= len(argument) <= max_channel_length):
            raise BadArgument("Channel name must be between 2 and 96 chars long")

        if not all(c.isalnum() or c in self.ALLOWED_CHARACTERS for c in argument):
            raise BadArgument(
                "Channel name must only consist of "
                "alphanumeric characters, minus signs or apostrophes."
            )

        # Replace invalid characters with unicode alternatives.
        return argument


class ValidCharacterObject(Converter):
    """A converter that ensures a character exists."""

    async def convert(self, ctx: Context, argument: str) -> Character:
        """Return a character object from a character id."""
        try:
            return ctx.bot.char_svc.fetch_by_id(ctx.guild.id, int(argument))
        except CharacterNotFoundError as e:
            raise BadArgument(str(e)) from e


class ValidClan(Converter):
    """A converter that ensures a requested vampire clan is valid."""

    async def convert(self, ctx: Context, argument: str) -> VampireClan:  # noqa: ARG002
        """Validate and normalize character's clan."""
        for c in DBConstants.vampire_clans():
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid vampire clan")


class ValidThumbnailURL(Converter):
    """Converter that ensures a requested thumbnail URL is valid."""

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize thumbnail URLs."""
        if not re.match(r"^https?://", argument):
            raise BadArgument("Thumbnail URLs must start with `http://` or `https://`")

        if not re.match(r".+\.(png|jpg|jpeg|gif)$", argument):
            raise BadArgument("Thumbnail URLs must end with a valid image extension")

        async with aiohttp.ClientSession() as session, session.get(argument) as r:
            success_status_codes = [200, 201, 202, 203, 204, 205, 206]
            if r.status not in success_status_codes:
                raise BadArgument(f"Thumbnail URL could not be accessed\nStatus: {r.status}")

        # Replace media.giphy.com URLs with i.giphy.com URLs
        return re.sub(r"//media\.giphy\.com", "//i.giphy.com", argument)


class ValidTraitCategory(Converter):
    """A converter that ensures a requested trait category is valid."""

    async def convert(self, ctx: Context, argument: str) -> TraitCategory:  # noqa: ARG002
        """Validate and normalize trait categories."""
        for c in DBConstants.trait_categories():
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid trait category")
