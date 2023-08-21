"""Converters, validators, and normalizers for Valentina."""

import re
from datetime import datetime

import aiohttp
from discord.ext import commands
from discord.ext.commands import BadArgument, Converter
from peewee import DoesNotExist, fn

from valentina.models.db_tables import (
    Character,
    CharacterClass,
    Chronicle,
    CustomSection,
    CustomTrait,
    Macro,
    Trait,
    TraitCategory,
    VampireClan,
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
            raise BadArgument("Channel name must be between 2 and 96 chars long")

        if not all(c.isalnum() or c in self.ALLOWED_CHARACTERS for c in argument):
            raise BadArgument(
                "Channel name must only consist of "
                "alphanumeric characters, minus signs or apostrophes."
            )

        # Replace invalid characters with unicode alternatives.
        return argument


class ValidCharacterClass(Converter):
    """A converter that ensures a requested character class name is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> CharacterClass:  # noqa: ARG002
        """Validate and normalize character classes."""
        for c in CharacterClass.select().order_by(CharacterClass.name.asc()):
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid character class")


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
        try:
            return Character.get_by_id(int(argument))
        except DoesNotExist as e:
            raise errors.DatabaseError(
                f"No character found in database with id `{argument}`"
            ) from e


class ValidCharTrait(Converter):
    """A converter that ensures a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> Trait | CustomTrait:
        """Validate and normalize traits."""
        character = ctx.bot.char_svc.fetch_claim(ctx)

        for trait in character.traits_list:
            if argument.lower() == trait.name.lower():
                return trait

        raise BadArgument(f"`{argument}` is not a valid trait")


class ValidChronicle(Converter):
    """A converter to grab a chronicle object from it's name."""

    async def convert(self, ctx: commands.Context, argument: str) -> Chronicle:
        """Convert from name to chronicle object."""
        chronicle = Chronicle.get_or_none(
            (fn.lower(Chronicle.name) == argument.lower()) & (Chronicle.guild_id == ctx.guild.id)
        )
        if chronicle:
            return chronicle

        raise (BadArgument(f"Chronicle {argument} not found"))


class ValidClan(Converter):
    """A converter that ensures a requested vampire clan is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> VampireClan:  # noqa: ARG002
        """Validate and normalize character's clan."""
        for c in VampireClan.select().order_by(VampireClan.name.asc()):
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid vampire clan")


class ValidCustomSection(Converter):
    """Converter to ensure a custom section is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> CustomSection:
        """Validate and return a custom section."""
        character = ctx.bot.char_svc.fetch_claim(ctx)

        for cs in CustomSection.select().where(CustomSection.character == character):
            if argument.lower() == cs.title.lower():
                return cs

        raise errors.DatabaseError(f"`{argument}` is not a valid custom section")


class ValidCustomTrait(Converter):
    """Converter to ensure a custom trait is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> CustomTrait:
        """Validate and return a custom trait."""
        character = ctx.bot.char_svc.fetch_claim(ctx)

        for ct in CustomTrait.select().where(CustomTrait.character == character):
            if argument.lower() == ct.name.lower():
                return ct

        raise BadArgument(f"`{argument}` is not a valid vampire clan")


class ValidThumbnailURL(Converter):
    """Converter that ensures a requested thumbnail URL is valid."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # noqa: ARG002
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

    async def convert(self, ctx: commands.Context, argument: str) -> TraitCategory:  # noqa: ARG002
        """Validate and normalize trait categories."""
        for c in TraitCategory.select().order_by(TraitCategory.name.asc()):
            if argument.lower() == c.name.lower():
                return c

        raise BadArgument(f"`{argument}` is not a valid trait category")


class ValidYYYYMMDD(Converter):
    """A converter that ensures a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> datetime:  # noqa: ARG002
        """Validate and normalize traits."""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", argument):
            return datetime.strptime(argument, "%Y-%m-%d")

        raise BadArgument(f"`{argument}` is not a valid trait")


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

        raise BadArgument(f"`{argument}` is not a valid trait")


class ValidTraitOrCustomTrait(Converter):
    """A converter to ensure a requested trait is a valid character trait or custom trait."""

    async def convert(self, ctx: commands.Context, argument: str) -> Trait | CustomTrait:
        """Validate and normalize traits."""
        character = ctx.bot.char_svc.fetch_claim(ctx)

        for trait in character.traits_list:
            if argument.lower() == trait.name.lower():
                return trait

        raise BadArgument(f"`{argument}` is not a valid trait")
