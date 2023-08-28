"""Models for working with characters in the database."""

import discord
from loguru import logger

from valentina.models.db_tables import Character, CustomSection
from valentina.utils.helpers import time_now


class CharacterService:
    """A service for managing the Player characters in the database."""

    def custom_section_update_or_add(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        section_title: str | None = None,
        section_description: str | None = None,
        section_id: int | None = None,
    ) -> CustomSection:
        """Update or add a custom section to a character.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character): The character object to which the custom section will be added.
            section_title (str | None): The title of the custom section. Defaults to None.
            section_description (str | None): The description of the custom section. Defaults to None.
            section_id (int | None): The id of an existing custom section. Defaults to None.

        Returns:
            CustomSection: The updated or created custom section.
        """
        ctx.bot.user_svc.purge_cache(ctx)  # type: ignore [attr-defined]

        if not section_id:
            logger.debug(f"DATABASE: Add custom section to {character}")
            section = CustomSection.create(
                title=section_title,
                description=section_description,
                character=character,
            )

        if section_id:
            section = CustomSection.get_by_id(section_id)
            section.title = section_title
            section.description = section_description
            section.save()

            logger.debug(f"DATABASE: Update custom section for {character}")

        return section

    def set_character_default_values(self) -> None:
        """Set default values for all characters in the database."""
        characters = Character.select()
        for character in characters:
            character.set_default_data_values()

    def fetch_all_player_characters(
        self, ctx: discord.ApplicationContext | discord.AutocompleteContext
    ) -> list[Character]:
        """Fetch all characters for a specific guild and confirm that default data values are set before returning them as a list.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext): Context object containing guild information.

        Returns:
            list[Character]: List of characters for the guild.
        """
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        characters = Character.select().where(
            Character.guild_id == guild_id, Character.data["player_character"] == True  # noqa: E712
        )
        logger.debug(f"DATABASE: Fetch {len(characters)} characters for guild `{guild_id}`")

        # Verify default data values are set
        to_return = []
        for c in characters:
            character = c.set_default_data_values()
            to_return.append(character)

        return to_return

    def fetch_all_storyteller_characters(
        self, ctx: discord.ApplicationContext | discord.AutocompleteContext
    ) -> list[Character]:
        """Fetch all StoryTeller characters for a guild.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext, optional): Context object containing guild information.

        Returns:
            list[Character]: List of StoryTeller characters for the guild.
        """
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        characters = Character.select().where(
            Character.guild_id == guild_id,
            Character.data["storyteller_character"] == True,  # noqa: E712
        )
        logger.debug(
            f"DATABASE: Fetch {len(characters)} storyteller characters for guild `{guild_id}`"
        )

        # Verify default data values are set
        to_return = []
        for c in characters:
            character = c.set_default_data_values()
            to_return.append(character)

        return to_return

    def update_or_add(
        self,
        ctx: discord.ApplicationContext,
        data: dict[str, str | int | bool] | None = None,
        character: Character | None = None,
        **kwargs: str | int,
    ) -> Character:
        """Update or add a character.

        Args:
            ctx (ApplicationContext): The application context.
            data (dict[str, str | int | bool] | None): The character data.
            character (Character | None): The character to update, or None to create.
            **kwargs: Additional fields for the character.

        Returns:
            Character: The updated or created character.
        """
        # Always add the modified timestamp if data is provided.
        if data:
            data["modified"] = str(time_now())

        if not character:
            user = ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

            new_character = Character.create(
                guild_id=ctx.guild.id,
                created_by=user,
                owned_by=user,
                data=data or {},
                **kwargs,
            )
            character = new_character.set_default_data_values()

            logger.info(f"DATABASE: Create {character} for {ctx.author.display_name}")

            return character

        if data:
            # FIXME: Log each key and value being updated.
            for key, value in data.items():
                logger.debug(f"DATABASE: Update {character} `{key}:{value}`")

            Character.update(data=Character.data.update(data)).where(
                Character.id == character.id
            ).execute()

        if kwargs:
            Character.update(**kwargs).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Updated Character '{character}'")

        return Character.get_by_id(character.id)  # Have to query db again to get updated data ???
