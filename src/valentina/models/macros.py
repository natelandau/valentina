"""Models for working with macros."""
from __future__ import annotations

import discord
from loguru import logger

from valentina.models.db_tables import CustomTrait, Macro, MacroTrait, Trait


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
        name: str,
        trait_one: Trait | CustomTrait,
        trait_two: Trait | CustomTrait,
        abbreviation: str | None = None,
        description: str | None = None,
    ) -> Macro:
        """Create a macro and associated macro traits."""
        existing_macros = self.fetch_macros(ctx.guild.id, ctx.author.id)

        if len(existing_macros) > 0 and (
            any(macro.name.lower() == name.lower() for macro in existing_macros)
            or (
                abbreviation is not None
                and any(
                    macro.abbreviation.lower() == abbreviation.lower() for macro in existing_macros
                )
            )
        ):
            logger.debug(f"CACHE: Macro already exists for {ctx.author.display_name}")
            raise ValueError("Macro already exists")

        logger.debug(f"DATABASE: Create macro {name} for {ctx.author.display_name}")
        macro = Macro.create(
            name=name,
            abbreviation=abbreviation,
            description=description,
            user=ctx.author.id,
            guild=ctx.guild.id,
        )
        MacroTrait.create_from_trait_name(macro, trait_one.name)
        MacroTrait.create_from_trait_name(macro, trait_two.name)
        self.purge(ctx)

        return macro

    def delete_macro(self, ctx: discord.ApplicationContext, macro: Macro) -> None:
        """Delete the macro and associated macro traits."""
        logger.debug(f"DATABASE: Delete macro {macro.name} for {ctx.author.display_name}")
        macro.delete_instance(recursive=True, delete_nullable=True)
        self.purge(ctx)

    def fetch_macros(self, guild_id: int, user_id: int) -> list[Macro]:
        """Fetch the macros for the given guild and user.

        Args:
            guild_id (discord.Guild | int): The guild to get the macros for.
            user_id (discord.User | int): The user to get the macros for.

        Returns:
            list[Macro]: The list of macros.
        """
        user_key = self.__get_user_key(guild_id, user_id)

        if user_key not in self._macro_cache:
            logger.debug(f"DATABASE: Fetch macros for {user_id}")

            self._macro_cache[user_key] = [
                x
                for x in Macro.select()
                .where((Macro.guild == guild_id) & (Macro.user == user_id))
                .order_by(Macro.name.asc())
            ]
        else:
            logger.debug(f"CACHE: Fetch macros for {user_id}")

        return self._macro_cache[user_key]

    def fetch_macro_traits(self, macro: Macro) -> list[Trait | CustomTrait]:
        """Fetch the Trait and Custom Traits associated with a macro."""
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

    def purge(self, ctx: discord.ApplicationContext | None = None) -> None:
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
