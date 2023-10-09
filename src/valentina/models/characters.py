"""Models for working with characters in the database."""
from typing import Literal

import discord
from loguru import logger
from numpy.random import default_rng

from valentina.constants import CharClassType, CharConcept, RNGCharLevel, VampireClanType
from valentina.models.db_tables import (
    Character,
    CharacterClass,
    CustomSection,
    GuildUser,
    VampireClan,
)
from valentina.utils.helpers import fetch_random_name, time_now
from valentina.utils.rng_trait_values import RNGTraitValues

_rng = default_rng()


class CharacterService:
    """A service for managing the Player characters in the database."""

    async def add_character_image(
        self, ctx: discord.ApplicationContext, character: Character, extension: str, data: bytes
    ) -> str:
        """Add an image to a character and upload it to Amazon S3.

        This function generates a unique key for the image, uploads the image to S3, and updates the character in the database to include the new image.

        Args:
            ctx (ApplicationContext): The application context.
            character (Any): The character object to which the image will be added.
            extension (str): The file extension of the image.
            data (bytes): The image data in bytes.

        Returns:
            str: The key to the image in Amazon S3.
        """
        # Get a list of the character's current images
        current_character_images = character.data.get("images", [])

        # Generate the key for the image
        key_prefix = ctx.bot.aws_svc.get_key_prefix(ctx, "character", character_id=character.id).rstrip("/")  # type: ignore [attr-defined]
        image_number = len(current_character_images) + 1
        image_name = f"{image_number}.{extension}"
        key = f"{key_prefix}/{image_name}"

        # Upload the image to S3
        ctx.bot.aws_svc.upload_image(data=data, key=key)  # type: ignore [attr-defined]

        # Add the image to the character's data
        current_character_images.append(key)
        await self.update_or_add(
            ctx, character=character, data={"images": current_character_images}
        )

        return key

    async def delete_character_image(
        self, ctx: discord.ApplicationContext, character: Character, key: str
    ) -> None:
        """Delete a character's image from both the character data and Amazon S3.

        This method updates the character's data to remove the image reference
        and also deletes the actual image stored in Amazon S3.

        Args:
            ctx (discord.ApplicationContext): The context containing the bot object.
            character (Character): The character object to update.
            key (str): The key representing the image to be deleted.

        Returns:
            None
        """
        # Remove image key from character's data
        character_images = character.data.get("images", [])
        character_images.remove(key)
        await self.update_or_add(ctx, character=character, data={"images": character_images})
        logger.debug(f"DATA: Removed image key '{key}' from character '{character.name}'")

        # Delete the image from Amazon S3
        ctx.bot.aws_svc.delete_object(key)  # type: ignore [attr-defined]
        logger.info(f"S3: Deleted {key} from {character}")

    @staticmethod
    def custom_section_update_or_add(
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

    @staticmethod
    def set_character_default_values() -> None:
        """Set default values for all characters in the database."""
        logger.info("DATABASE: Set default values for all characters")
        characters = Character.select()
        for character in characters:
            character.set_default_data_values()

    @staticmethod
    def fetch_all_player_characters(
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
        owned_by: GuildUser | None = None,
    ) -> list[Character]:
        """Fetch all characters for a specific guild and confirm that default data values are set before returning them as a list.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext): Context object containing guild information.
            owned_by (discord.Member | None, optional): Limit response to a single member who owns the characters. Defaults to None.

        Returns:
            list[Character]: List of characters for the guild.
        """
        guild_id = (
            ctx.guild.id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.interaction.guild.id
        )

        if owned_by:
            characters = Character.select().where(
                Character.guild_id == guild_id,
                Character.data["player_character"] == True,  # noqa: E712
                Character.owned_by == owned_by.id,
            )
        else:
            characters = Character.select().where(
                Character.guild_id == guild_id,
                Character.data["player_character"] == True,  # noqa: E712
            )
        logger.debug(f"DATABASE: Fetch {len(characters)} characters for guild `{guild_id}`")

        # Verify default data values are set
        to_return = []
        for c in characters:
            character = c.set_default_data_values()
            to_return.append(character)

        return to_return

    @staticmethod
    def fetch_all_storyteller_characters(
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
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

    @staticmethod
    async def update_or_add(
        ctx: discord.ApplicationContext,
        data: dict[str, str | int | bool] | None = None,
        character: Character | None = None,
        char_class: CharClassType | None = CharClassType.NONE,
        clan: VampireClanType | None = None,
        **kwargs: str | int,
    ) -> Character:
        """Update or add a character.

        Args:
            ctx (ApplicationContext): The application context.
            data (dict[str, str | int | bool] | None): The character data.
            character (Character | None): The character to update, or None to create.
            char_class (CharClassType | None): The character class.
            clan (VampireClanType | None): The vampire clan.
            **kwargs: Additional fields for the character.

        Returns:
            Character: The updated or created character.
        """
        # Purge the user's character cache
        ctx.bot.user_svc.purge_cache(ctx)  # type: ignore [attr-defined]

        # Always add the modified timestamp if data is provided.
        if data:
            data["modified"] = str(time_now())

        if not character:
            user = await ctx.bot.user_svc.fetch_user(ctx)  # type: ignore [attr-defined] # it really is defined

            new_character = Character.create(
                guild_id=ctx.guild.id,
                created_by=user,
                owned_by=user,
                char_class=CharacterClass.get_or_none(name=char_class.name),
                clan=VampireClan.get_or_none(name=clan.name) if clan else None,
                data=data or {},
                **kwargs,
            )
            character = new_character.set_default_data_values()

            logger.info(f"DATABASE: Create {character} for {ctx.author.display_name}")

            return character

        if data:
            Character.update(data=Character.data.update(data)).where(
                Character.id == character.id
            ).execute()

        if kwargs:
            Character.update(**kwargs).where(Character.id == character.id).execute()

        logger.debug(f"DATABASE: Updated Character '{character}'")

        return Character.get_by_id(character.id)  # Have to query db again to get updated data ???

    async def rng_creator(
        self,
        ctx: discord.ApplicationContext,
        char_class: CharClassType | None = None,
        concept: CharConcept | None = None,
        vampire_clan: VampireClanType | None = None,
        character_level: RNGCharLevel | None = None,
        player_character: bool = False,
        storyteller_character: bool = False,
        developer_character: bool = False,
        chargen_character: bool = False,
        gender: Literal["male", "female"] | None = None,
        nationality: str = "us",
        nickname_is_class: bool = False,
    ) -> Character:
        """Create a random character."""
        # Add a random name

        name = await fetch_random_name(gender=gender, country=nationality)
        first_name, last_name = name[0]

        data: dict[str, str | int | bool] = {
            "first_name": first_name,
            "last_name": last_name,
        }

        # Add character metadata
        if char_class is None:
            percentile = _rng.integers(1, 101)
            char_class = CharClassType.get_member_by_value(percentile)

        if nickname_is_class:
            data["nickname"] = char_class.value["name"]

        if concept is None:
            percentile = _rng.integers(1, 101)
            concept = CharConcept.get_member_by_value(percentile)
        data["concept_human"] = concept.value["name"]
        data["concept_db"] = concept.name

        if character_level is None:
            character_level = RNGCharLevel.random_member()
        data["rng_level"] = character_level.name.title()

        if char_class == CharClassType.VAMPIRE and not vampire_clan:
            vampire_clan = VampireClanType.random_member()

        data["player_character"] = player_character
        data["storyteller_character"] = storyteller_character
        data["developer_character"] = developer_character
        data["chargen_character"] = chargen_character

        # Add character to database
        character = await self.update_or_add(
            ctx,
            char_class=CharacterClass.get(name=char_class.name),
            clan=VampireClan(name=vampire_clan.name) if vampire_clan else None,
            data=data,
        )

        rng_traits = RNGTraitValues(
            ctx=ctx, character=character, concept=concept, level=character_level
        )
        character = rng_traits.set_trait_values()
        # TODO: Add specialties, backgrounds, etc.
        logger.debug(f"CHARGEN: Created {character} from RNG")
        return character
