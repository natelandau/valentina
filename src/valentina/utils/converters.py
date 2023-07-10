"""Converters, validators, and normalizers for Valentina."""


import re

from discord.ext.commands import BadArgument, Context, Converter

from valentina.models.constants import CharClass, VampClanList


class ValidThumbnailURL(Converter):
    """Converter that ensures a requested thumbnail URL is valid."""

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize thumbnail URLs."""
        if not re.match(r"^https?://", argument):
            raise BadArgument("Thumbnail URLs must start with `http://` or `https://`")

        if not re.match(r".+\.(png|jpg|jpeg|gif)$", argument):
            raise BadArgument("Thumbnail URLs must end with a valid image extension")

        # Replace media.giphy.com URLs with i.giphy.com URLs
        return re.sub(r"//media\.giphy\.com", "//i.giphy.com", argument)


class ValidCharacterClass(Converter):
    """A converter that ensures a requested character class is valid."""

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize character classes."""
        try:
            return CharClass(argument).value
        except ValueError as e:
            raise BadArgument(f"`{argument}` is not a valid character class") from e


class ValidClan(Converter):
    """A converter that ensures a requested vampire clan is valid."""

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        """Validate and normalize character's clan."""
        try:
            return VampClanList(argument).value
        except ValueError as e:
            raise BadArgument(f"`{argument}` is not a valid vampire clan") from e


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
