"""Models for working with macros."""
from __future__ import annotations

import discord
from loguru import logger

from valentina.models.db_tables import CustomTrait, GuildUser, Macro, MacroTrait, Trait
from valentina.utils import errors


class MacroService:
    """Class for managing macros and an in-memory cache."""

    def __init__(self) -> None:
        self._macro_cache: dict[str, list[Macro]] = {}  # {user_key: [macros]}
        self._trait_cache: dict[int, list[Trait | CustomTrait]] = {}  # {macro.id: [traits]}

    @staticmethod
    def __get_user_key(guild_id: int, user_id: int) -> str:
        """Get the guild and user IDs.

        Args:
            guild_id (discord.Guild | int): The guild to get the ID for.
            user_id (discord.User | int): The user to get the ID for.

        Returns:
            str: The guild and user IDs joined by an underscore.
        """
        return f"{guild_id}_{user_id}"

    def create_macro(
        self,
        ctx: discord.ApplicationContext,
        user: GuildUser,
        name: str,
        trait_one: Trait | CustomTrait,
        trait_two: Trait | CustomTrait,
        abbreviation: str | None = None,
        description: str | None = None,
    ) -> Macro:
        """Create a macro and associated macro traits."""
        existing_macros = self.fetch_macros(user)

        # Check if a macro with the same name already exists
        if any(macro.name.lower() == name.lower() for macro in existing_macros):
            logger.debug(f"CACHE: Macro already exists for {user}")
            raise errors.ValidationError(f"Macro named `{name}` already exists.")

        # Check if a macro with the same abbreviation already exists
        if abbreviation is not None and any(
            macro.abbreviation.lower() == abbreviation.lower() for macro in existing_macros
        ):
            logger.debug(f"CACHE: Macro already exists for {user}")
            raise errors.ValidationError("Macro with the same abbreviation already exists.")

        # Create the macro and associated macro traits
        logger.debug(f"DATABASE: Create macro {name} for {user}")
        macro = Macro.create(
            name=name,
            abbreviation=abbreviation,
            description=description,
            user=user,
            guild=user.guild.id,
        )
        MacroTrait.create_from_trait(macro, trait_one)
        MacroTrait.create_from_trait(macro, trait_two)

        # Purge the cache to ensure consistency
        self.purge_cache(ctx)

        return macro  # Return the created macro

    def delete_macro(self, ctx: discord.ApplicationContext, macro: Macro) -> None:
        """Delete the macro and associated macro traits.

        Args:
            ctx: The Discord application context.
            macro: The macro to delete.

        Raises:
            ValueError: If the macro does not belong to the user.
        """
        logger.debug(f"DATABASE: Delete macro {macro.name} for {ctx.author.display_name}")
        macro.delete_instance(recursive=True, delete_nullable=True)
        self.purge_cache(ctx)

    def fetch_macros(self, user: GuildUser) -> list[Macro]:
        """Fetch the macros for the given guild and user.

        Args:
            user (GuildUser): The user to fetch macros for.

        Returns:
            list[Macro]: The list of macros.
        """
        user_key = self.__get_user_key(user.guild.id, user.user)

        if user_key not in self._macro_cache:
            logger.debug(f"DATABASE: Fetch macros for {user}")

            self._macro_cache[user_key] = [
                x for x in Macro.select().where(Macro.user == user).order_by(Macro.name.asc())
            ]
        else:
            logger.debug(f"CACHE: Fetch macros for {user}")

        return self._macro_cache[user_key]

    def fetch_macro_traits(self, macro: Macro) -> list[Trait | CustomTrait]:
        """Fetch all traits for a given macro.

        Args:
            macro: The macro to fetch traits for.

        Returns:
            list: A list of MacroTrait objects.
        """
        if macro.id not in self._trait_cache:
            logger.debug(f"DATABASE: Fetch traits for {macro.name}")
            trait_objects = Trait.select().join(MacroTrait).where(MacroTrait.macro == macro)
            custom_trait_objects = (
                CustomTrait.select().join(MacroTrait).where(MacroTrait.macro == macro)
            )
            self._trait_cache[macro.id] = list(trait_objects) + list(custom_trait_objects)
        else:
            logger.debug(f"CACHE: Fetch traits for {macro.name}")

        return self._trait_cache[macro.id]

    def purge_cache(self, ctx: discord.ApplicationContext | None = None) -> None:
        """Purge the macro cache."""
        if ctx:
            logger.debug(f"CACHE: Purge macros for {ctx.author.display_name}")
            user_key = self.__get_user_key(ctx.guild.id, ctx.author.id)

            if user_key in self._macro_cache:
                for macro in self._macro_cache[user_key]:
                    self._trait_cache.pop(macro.id, None)

            self._macro_cache.pop(user_key, None)
        else:
            logger.debug("CACHE: Purge all macros from cache")
            self._macro_cache.clear()
            self._trait_cache.clear()

    def fetch_macro_from_traits(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Trait | CustomTrait,
        trait_two: Trait | CustomTrait,
    ) -> Macro:
        """Check if a macro already exists for the given user and for the given traits."""
        user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

        existing_macros = self.fetch_macros(user)

        for macro in existing_macros:
            traits = self.fetch_macro_traits(macro)

            if trait_one in traits and trait_two in traits:
                return macro

        return None
