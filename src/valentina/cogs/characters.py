# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.constants import (
    VALID_IMAGE_EXTENSIONS,
    EmbedColor,
    Emoji,
)
from valentina.models.bot import Valentina
from valentina.utils import errors
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterName,
    ValidCharacterObject,
    ValidCharTrait,
    ValidClan,
    ValidCustomSection,
    ValidCustomTrait,
    ValidImageURL,
    ValidTraitCategory,
    ValidYYYYMMDD,
)
from valentina.utils.helpers import (
    fetch_data_from_url,
    truncate_string,
)
from valentina.utils.options import (
    select_any_player_character,
    select_char_class,
    select_char_trait,
    select_custom_section,
    select_custom_trait,
    select_player_character,
    select_trait_category,
    select_vampire_clan,
)
from valentina.views import (
    BioModal,
    CharGenWizard,
    CustomSectionModal,
    ProfileModal,
    S3ImageReview,
    confirm_action,
    present_embed,
    show_sheet,
)

p = inflect.engine()


class Characters(commands.Cog, name="Character"):
    """Create, manage, and update characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    chars = discord.SlashCommandGroup("character", "Work with characters")
    bio = chars.create_subgroup("bio", "Add or update a character's biography")
    image = chars.create_subgroup("image", "Add or update character images")
    profile = chars.create_subgroup("profile", "Nature, Demeanor, DOB, and other profile traits")
    section = chars.create_subgroup("section", "Work with character custom sections")
    trait = chars.create_subgroup("trait", "Work with character traits")

    @chars.command(name="create", description="Create a new character")
    async def create_character(
        self,
        ctx: discord.ApplicationContext,
        char_class: Option(
            ValidCharacterClass,
            name="char_class",
            description="The character's class",
            autocomplete=select_char_class,
            required=True,
        ),
        first_name: Option(ValidCharacterName, "Character's name", required=True),
        last_name: Option(ValidCharacterName, "Character's last name", required=True),
        nickname: Option(ValidCharacterName, "Character's nickname", required=False, default=None),
        vampire_clan: Option(
            ValidClan,
            name="vampire_clan",
            description="The character's clan (only for vampires)",
            autocomplete=select_vampire_clan,
            required=False,
            default=None,
        ),
    ) -> None:
        """Create a new character.

        Args:
            char_class (CharacterClass): The character's class
            ctx (discord.ApplicationContext): The context of the command
            first_name (str): The character's first name
            last_name (str, optional): The character's last name. Defaults to None.
            nickname (str, optional): The character's nickname. Defaults to None.
            vampire_clan (VampireClan, optional): The character's vampire clan. Defaults to None.
        """
        # Ensure the user is in the database
        await self.bot.user_svc.update_or_add(ctx)

        # Require a clan for vampires
        if char_class.name.lower() == "vampire" and not vampire_clan:
            await present_embed(
                ctx,
                title="Vampire clan required",
                description="Please select a vampire clan",
                level="error",
            )
            return

        # Fetch all traits and set them
        fetched_traits = self.bot.trait_svc.fetch_all_class_traits(char_class.name)

        wizard = CharGenWizard(
            ctx,
            fetched_traits,
            first_name=first_name,
            last_name=last_name,
            nickname=nickname,
        )
        await wizard.begin_chargen()
        trait_values_from_chargen = await wizard.wait_until_done()

        # Create the character and traits in the db
        data: dict[str, str | int | bool] = {
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname,
            "player_character": True,
        }

        # Make character active if user does not have an active character
        try:
            await self.bot.user_svc.fetch_active_character(ctx)
        except errors.NoActiveCharacterError:
            data["is_active"] = True

        character = await self.bot.char_svc.update_or_add(
            ctx, data=data, char_class=char_class, clan=vampire_clan
        )

        for trait, value in trait_values_from_chargen:
            character.set_trait_value(trait, value)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Created player character: `{character.full_name}` as a `{char_class.name}`"
        )
        logger.info(f"CHARACTER: Create character {character}")

    @chars.command(name="set_active", description="Select a character as your active character")
    async def set_active_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_player_character,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Select a character as your active character."""
        if not character.is_alive:
            title = (
                f"{character.name} is dead. Set as active for `{ctx.author.display_name}` anyway"
            )
        else:
            title = f"Set `{character.name}` as active character for `{ctx.author.display_name}`"

        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        await self.bot.user_svc.set_active_character(ctx, character)

        await confirmation_response_msg

    @chars.command(name="sheet", description="View a character sheet")
    async def view_character_sheet(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_any_player_character,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the sheet only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Displays a character sheet in the channel."""
        await show_sheet(ctx, character=character, ephemeral=hidden)

    @chars.command(name="list", description="List all characters")
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
        scope: Option(
            str,
            description="Scope of characters to list",
            default="all",
            choices=["all", "mine"],
        ),
        hidden: Option(
            bool,
            description="Make the list only visible to you (default false).",
            default=False,
        ),
    ) -> None:
        """List all player characters in this guild."""
        if scope == "all":
            characters = self.bot.char_svc.fetch_all_player_characters(ctx)
            title_prefix = "All player"
        elif scope == "mine":
            user = await self.bot.user_svc.fetch_user(ctx)
            characters = self.bot.char_svc.fetch_all_player_characters(ctx, owned_by=user)
            title_prefix = "Your"

        if len(characters) == 0:
            await present_embed(
                ctx,
                title="No Characters",
                description="There are no characters.\nCreate one with `/character create`",
                level="warning",
                ephemeral=hidden,
            )
            return

        text = (
            f"## {title_prefix} {p.plural_noun('character', len(characters))} on {ctx.guild.name}\n"
        )

        for character in sorted(characters, key=lambda x: x.name):
            alive = Emoji.ALIVE.value if character.is_alive else Emoji.DEAD.value
            text += f"**{character.name}**\n"
            text += "```\n"
            text += f"Class: {character.char_class.name:<20}  Created On: {character.created.split(' ')[0]}\n"
            text += f"Owner: {character.owned_by.data['display_name']:<20} Lifetime XP: {character.data['experience']}\n"
            text += f"Alive: {alive:<20}  Active: {character.is_active}\n"
            text += "```\n"

        embed = discord.Embed(description=text, color=EmbedColor.INFO.value)
        await ctx.respond(embed=embed, ephemeral=hidden)

    @chars.command(name="transfer", description="Transfer one of your characters to another user")
    async def transfer_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_player_character,
            required=True,
        ),
        new_owner: Option(discord.User, description="The user to transfer the character to"),
        hidden: Option(
            bool,
            description="Make the sheet only visible to you (default false).",
            default=False,
        ),
    ) -> None:
        """Transfer one of your characters to another user."""
        title = f"Transfer `{character.name}` from `{ctx.author.display_name}` to `{new_owner.display_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        await self.bot.user_svc.transfer_character_owner(ctx, character, new_owner)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @chars.command(name="kill", description="Kill a character")
    async def kill_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_any_player_character,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Kill a character."""
        if not self.bot.user_svc.can_kill_character(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description=f"You do not have permissions to kill {character.full_name}\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        title = f"Kill `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        updates: dict[str, str | int | bool] = {"is_active": False, "is_alive": False}
        await self.bot.char_svc.update_or_add(ctx, character=character, data=updates)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    ### IMAGE COMMANDS ####################################################################
    @image.command(name="add", description="Add an image to a character")
    async def add_image(
        self,
        ctx: discord.ApplicationContext,
        file: Option(
            discord.Attachment,
            description="Location of the image on your local computer",
            required=False,
            default=None,
        ),
        url: Option(
            ValidImageURL, description="URL of the thumbnail", required=False, default=None
        ),
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add an image to a character.

        This function allows the user to add an image to a character either by uploading a file or providing a URL. It performs validation checks on the image, confirms the action with the user, and then uploads the image.

        Args:
            ctx (ApplicationContext): The application context.
            file (discord.Attachment): The image file to be uploaded.
            url (ValidImageURL): The URL of the image to be uploaded.
            hidden (bool): Whether the interaction should only be visible to the user initiating it.

        Returns:
            None
        """
        # Validate input
        if (not file and not url) or (file and url):
            await present_embed(ctx, title="Please provide a single image", level="error")
            return

        if file:
            file_extension = Path(file.filename).suffix.lstrip(".").lower()
            if file_extension not in VALID_IMAGE_EXTENSIONS:
                await present_embed(
                    ctx,
                    title=f"Must provide a valid image: {', '.join(VALID_IMAGE_EXTENSIONS)}",
                    level="error",
                )
                return

        # Fetch active character
        character = await self.bot.user_svc.fetch_active_character(ctx)

        # Upload the image to S3
        # We upload the image prior to the confirmation step to allow us to display the image to the user.  If the user cancels the confirmation, we must delete the image from S3.

        # Determine image extension and read data
        extension = file_extension if file else url.split(".")[-1].lower()
        data = await file.read() if file else await fetch_data_from_url(url)

        # Add image to character
        image_key = await self.bot.char_svc.add_character_image(ctx, character, extension, data)
        image_url = self.bot.aws_svc.get_url(image_key)

        title = f"Add image to `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, hidden=hidden, image=image_url
        )
        if not is_confirmed:
            await self.bot.char_svc.delete_character_image(ctx, character, image_key)
            return

        # Update audit log and original response
        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @image.command(name="delete", description="Delete an image from a character")
    async def delete_image(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete an image from a character.

        This function fetches the active character for the user, generates the key prefix for the character's images, and then initiates an S3ImageReview to allow the user to review and delete images.

        Args:
            ctx (ApplicationContext): The application context.
            hidden (bool): Whether the interaction should only be visible to the user initiating it.

        Returns:
            None
        """
        # Fetch the active character for the user
        character = await self.bot.user_svc.fetch_active_character(ctx)

        # Generate the key prefix for the character's images
        key_prefix = self.bot.aws_svc.get_key_prefix(
            ctx, "character", character_id=character.id
        ).rstrip("/")

        # Initiate an S3ImageReview to allow the user to review and delete images
        await S3ImageReview(ctx, key_prefix, review_type="character", hidden=hidden).send(ctx)

    ### TRAIT COMMANDS ####################################################################
    @trait.command(name="add", description="Add a trait to a character")
    async def add_custom_trait(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of of trait to add.", required=True),
        category: Option(
            ValidTraitCategory,
            name="category",
            description="The category to add the trait to",
            required=True,
            autocomplete=select_trait_category,
        ),
        value: Option(int, "The value of the trait", required=True, min_value=0, max_value=20),
        max_value: Option(
            int,
            "The maximum value of the trait (Defaults to 5)",
            required=False,
            min_value=1,
            max_value=20,
            default=5,
        ),
        description: Option(str, "A description of the trait", required=False),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a custom trait to a character."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        title = f"Create custom trait: `{name.title()}` at `{value}` dots for {character.full_name}"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        character.add_custom_trait(
            name=name,
            category=category,
            value=value,
            max_value=max_value,
            description=description,
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @trait.command(name="update", description="Update the value of a trait for a character")
    async def update_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            ValidCharTrait,
            description="Trait to update",
            required=True,
            autocomplete=select_char_trait,
        ),
        new_value: Option(
            int, description="New value for the trait", required=True, min_value=0, max_value=20
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update the value of a trait."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        if not self.bot.user_svc.can_update_traits(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to update traits on this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        old_value = character.get_trait_value(trait)

        title = (
            f"Update `{trait.name}` from `{old_value}` to `{new_value}` for `{character.full_name}`"
        )
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        character.set_trait_value(trait, new_value)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @trait.command(name="delete", description="Delete a custom trait from a character")
    async def delete_custom_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            ValidCustomTrait,
            description="Trait to delete",
            required=True,
            autocomplete=select_custom_trait,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        title = f"Delete custom trait `{trait.name}` from `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        trait.delete_instance()

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    ### SECTION COMMANDS ####################################################################

    @section.command(name="add", description="Add a new custom section to the character sheet")
    async def add_custom_section(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a custom section to the character sheet."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        modal = CustomSectionModal(
            title=truncate_string(f"Custom section for {character.full_name}", 45)
        )
        await ctx.send_modal(modal)
        await modal.wait()

        section_title = modal.section_title.strip().title()
        section_description = modal.section_description.strip()

        existing_sections = character.custom_sections
        if section_title.replace("-", "_").replace(" ", "_").lower() in [
            x.title.replace("-", "_").replace(" ", "_").lower() for x in existing_sections
        ]:
            raise errors.ValidationError("Custom section already exists")

        self.bot.char_svc.custom_section_update_or_add(
            ctx, character, section_title, section_description
        )

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Add section `{section_title}` to `{character.name}`"
        )

        await present_embed(
            ctx,
            f"Add section `{section_title}` to `{character.name}`",
            description=f"**{section_title}**\n{section_description}",
            ephemeral=hidden,
            level="success",
        )

    @section.command(name="update", description="Update a custom section")
    async def update_custom_section(
        self,
        ctx: discord.ApplicationContext,
        custom_section: Option(
            ValidCustomSection,
            description="Custom section to update",
            required=True,
            autocomplete=select_custom_section,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update a custom section."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        modal = CustomSectionModal(
            section_title=custom_section.title,
            section_description=custom_section.description,
            title=truncate_string(f"Custom section for {character.full_name}", 45),
        )
        await ctx.send_modal(modal)
        await modal.wait()

        section_title = modal.section_title.strip().title()
        section_description = modal.section_description.strip()

        self.bot.char_svc.custom_section_update_or_add(
            ctx,
            character,
            section_title=section_title,
            section_description=section_description,
            section_id=custom_section.id,
        )

        title = f"Update section `{section_title}` for `{character.name}`"
        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await present_embed(
            ctx,
            title=title,
            description=f"**{section_title}**\n{section_description}",
            ephemeral=hidden,
            level="success",
        )

    @section.command(name="delete", description="Delete a custom section from a character")
    async def delete_custom_section(
        self,
        ctx: discord.ApplicationContext,
        custom_section: Option(
            ValidCustomSection,
            description="Custom section to delete",
            required=True,
            autocomplete=select_custom_section,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        title = f"Delete section `{custom_section.title}` from `{character.full_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        custom_section.delete_instance()
        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    ### BIO COMMANDS ####################################################################

    @bio.command(name="update", description="Add or update a character's bio")
    async def update_bio(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update a character's bio."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        modal = BioModal(
            title=truncate_string(f"Enter the biography for {character.full_name}", 45),
            current_bio=character.data["bio"],
        )
        await ctx.send_modal(modal)
        await modal.wait()
        biography = modal.bio.strip()

        await self.bot.char_svc.update_or_add(ctx, character=character, data={"bio": biography})

        await self.bot.guild_svc.send_to_audit_log(ctx, f"Update biography for `{character.name}`")

        await present_embed(
            ctx,
            title=f"Update biography for `{character.name}`",
            description=f"**Biography**\n{biography}",
            level="success",
            ephemeral=hidden,
        )

    ### PROFiLE COMMANDS ####################################################################

    @profile.command(name="date_of_birth")
    async def date_of_birth(
        self,
        ctx: discord.ApplicationContext,
        dob: Option(ValidYYYYMMDD, description="DOB in the format of YYYY-MM-DD", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set the DOB of a character."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        await self.bot.char_svc.update_or_add(ctx, character=character, data={"date_of_birth": dob})

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"`{character.name}` DOB set to `{dob:%Y-%m-%d}`"
        )
        await present_embed(
            ctx,
            title="Date of Birth Updated",
            description=f"`{character.name}` DOB set to `{dob:%Y-%m-%d}`",
            level="success",
            ephemeral=hidden,
        )

    @profile.command(name="update", description="Update a character's profile")
    async def update_profile(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update a character's profile."""
        character = await self.bot.user_svc.fetch_active_character(ctx)

        modal = ProfileModal(
            title=truncate_string(f"Profile for {character}", 45), character=character
        )
        await ctx.send_modal(modal)
        await modal.wait()
        if modal.confirmed:
            update_data: dict = {}
            for k, v in modal.results.items():
                if v:
                    update_data[k] = v

            await self.bot.char_svc.update_or_add(ctx, character=character, data=update_data)

            await self.bot.guild_svc.send_to_audit_log(
                ctx, f"Update profile for `{character.name}`"
            )

            await present_embed(
                ctx,
                title=f"Update profile for `{character.name}`",
                level="success",
                ephemeral=hidden,
            )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
