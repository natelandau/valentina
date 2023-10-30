# mypy: disable-error-code="valid-type"
"""Character cog for Valentina."""
from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.characters import AddFromSheetWizard, CharGenWizard
from valentina.constants import (
    VALID_IMAGE_EXTENSIONS,
    CharClass,
    EmbedColor,
    Emoji,
    RNGCharLevel,
)
from valentina.models.aws import AWSService
from valentina.models.bot import Valentina, ValentinaContext
from valentina.models.mongo_collections import (
    Campaign,
    Character,
    CharacterSheetSection,
    Guild,
    User,
)
from valentina.utils import errors
from valentina.utils.converters import (
    ValidCharacterName,
    ValidCharacterObject,
    ValidCharClass,
    ValidClan,
    ValidCustomSection,
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
    select_player_character,
    select_trait_category,
    select_vampire_clan,
)
from valentina.views import (
    BioModal,
    CustomSectionModal,
    ProfileModal,
    S3ImageReview,
    confirm_action,
    present_embed,
    show_sheet,
)

p = inflect.engine()


class CharactersCog(commands.Cog, name="Character"):
    """Create, manage, and update characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot
        self.aws_svc = AWSService()

    chars = discord.SlashCommandGroup("character", "Work with characters")
    bio = chars.create_subgroup("bio", "Add or update a character's biography")
    image = chars.create_subgroup("image", "Add or update character images")
    profile = chars.create_subgroup("profile", "Nature, Demeanor, DOB, and other profile traits")
    section = chars.create_subgroup("section", "Work with character custom sections")
    trait = chars.create_subgroup("trait", "Work with character traits")

    async def _fetch_active_character(self, ctx: ValentinaContext) -> Character:
        """Fetch the active character for the user."""
        user = await User.get(ctx.author.id, fetch_links=True)
        return await user.active_character(ctx.guild)

    async def _fetch_active_campaign(self, ctx: ValentinaContext) -> Campaign:
        """Fetch the active campaign for the user."""
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        campaign = guild.active_campaign
        if not campaign:
            raise errors.NoActiveCampaignError

        return campaign

    @chars.command(name="add", description="Add a character to Valentina from a sheet")
    async def add_character(
        self,
        ctx: ValentinaContext,
        char_class: Option(
            ValidCharClass,
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
        """Add a character from a character sheet using the chargen wizard.

        Args:
            char_class (CharClass): The character's class
            ctx (discord.ApplicationContext): The context of the command
            first_name (str): The character's first name
            last_name (str, optional): The character's last name. Defaults to None.
            nickname (str, optional): The character's nickname. Defaults to None.
            vampire_clan (VampireClan, optional): The character's vampire clan. Defaults to None.
        """
        # Require a clan for vampires
        if char_class == CharClass.VAMPIRE and not vampire_clan:
            await present_embed(
                ctx,
                title="Vampire clan required",
                description="Please select a vampire clan",
                level="error",
            )
            return

        user = await User.get(ctx.author.id, fetch_links=True)
        character = Character(
            guild=ctx.guild.id,
            name_first=first_name,
            name_last=last_name,
            name_nick=nickname,
            char_class_name=char_class.name,
            clan_name=vampire_clan.name if vampire_clan else None,
            type_player=True,
            user_creator=user.id,
            user_owner=user.id,
        )

        wizard = AddFromSheetWizard(ctx, character=character, user=user)
        await wizard.begin_chargen()

    @chars.command(name="create", description="Create a new randomized character")
    async def create_character(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new character from scratch."""
        # Grab the current user and campaign experience
        user = await User.get(ctx.author.id, fetch_links=True)
        campaign = await self._fetch_active_campaign(ctx)
        campaign_xp, _, _ = user.fetch_campaign_xp(campaign)

        # Abort if user does not have enough xp
        if campaign_xp < 10:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Not enough xp",
                description="You do not have enough xp to create a new character",
                level="error",
                ephemeral=hidden,
            )
            return

        wizard = CharGenWizard(
            ctx, campaign=campaign, user=user, experience_level=RNGCharLevel.NEW, hidden=hidden
        )
        await wizard.start()

    @chars.command(name="set_active", description="Select a character as your active character")
    async def set_active_character(
        self,
        ctx: ValentinaContext,
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

        user = await User.get(ctx.author.id)
        await user.set_active_character(character)

        await confirmation_response_msg

    @chars.command(name="sheet", description="View a character sheet")
    async def view_character_sheet(
        self,
        ctx: ValentinaContext,
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
        ctx: ValentinaContext,
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
        all_characters = await Character.find_many(
            Character.guild == ctx.guild.id, Character.type_player == True  # noqa: E712
        ).to_list()

        if scope == "mine":
            all_characters = [x for x in all_characters if x.user_owner == ctx.user.id]

        if len(all_characters) == 0:
            await present_embed(
                ctx,
                title="No Characters",
                description="There are no characters.\nCreate one with `/character create`",
                level="warning",
                ephemeral=hidden,
            )
            return

        title_prefix = "All player" if scope == "all" else "Your"
        text = f"## {title_prefix} {p.plural_noun('character', len(all_characters))} on {ctx.guild.name}\n"

        for character in sorted(all_characters, key=lambda x: x.name):
            user = await character.fetch_owner()
            alive_emoji = Emoji.ALIVE.value if character.is_alive else Emoji.DEAD.value
            if user_active_character := await user.active_character(ctx.guild, raise_error=False):
                active = "True" if character.id == user_active_character.id else "False"
            else:
                active = "False"

            text += f"**{character.name}**\n"
            text += "```\n"
            text += f"Class: {character.char_class.name:<20}  Created On: {character.date_created.strftime('%Y-%m-%d')}\n"
            text += f"Alive: {alive_emoji:<20} Active: {active}\n"

            text += f"Owner: {user.name:<20}\n"
            text += "```\n"

        embed = discord.Embed(description=text, color=EmbedColor.INFO.value)
        await ctx.respond(embed=embed, ephemeral=hidden)

    @chars.command(name="transfer", description="Transfer one of your characters to another user")
    async def transfer_character(
        self,
        ctx: ValentinaContext,
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
        if new_owner == ctx.author:
            await present_embed(
                ctx,
                title="Cannot transfer to yourself",
                description="You cannot transfer a character to yourself",
                level="error",
                ephemeral=hidden,
            )
            return

        title = f"Transfer `{character.name}` from `{ctx.author.display_name}` to `{new_owner.display_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        current_user = await User.get(ctx.author.id, fetch_links=True)
        new_user = await User.get(new_owner.id, fetch_links=True)

        await current_user.remove_character(character)
        new_user.characters.append(character)
        await new_user.save()

        character.user_owner = new_user.id
        await character.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    @chars.command(name="kill", description="Kill a character")
    async def kill_character(
        self,
        ctx: ValentinaContext,
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
        # Guard statement: check permissions
        if not await ctx.can_kill_character(character):
            await present_embed(
                ctx,
                title="Permission error",
                description=f"You do not have permissions to kill {character.name}\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        title = f"Kill `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        character.is_alive = False
        await character.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    ### IMAGE COMMANDS ####################################################################
    @image.command(name="add", description="Add an image to a character")
    async def add_image(
        self,
        ctx: ValentinaContext,
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

        # Fetch the active character
        character = await self._fetch_active_character(ctx)

        # Determine image extension and read data
        extension = file_extension if file else url.split(".")[-1].lower()
        data = await file.read() if file else await fetch_data_from_url(url)

        # Upload image and add to character
        # We upload the image prior to the confirmation step to allow us to display the image to the user.  If the user cancels the confirmation, we must delete the image from S3 and from the character object.
        image_key = await character.add_image(extension=extension, data=data)
        image_url = self.aws_svc.get_url(image_key)

        title = f"Add image to `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, hidden=hidden, image=image_url
        )
        if not is_confirmed:
            await character.delete_image(image_key)
            return

        # Update audit log and original response
        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    @image.command(name="delete", description="Delete an image from a character")
    async def delete_image(
        self,
        ctx: ValentinaContext,
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
        # Fetch the active character
        character = await self._fetch_active_character(ctx)

        # Generate the key prefix for the character's images
        key_prefix = f"{ctx.guild.id}/characters/{character.id}"

        # Initiate an S3ImageReview to allow the user to review and delete images
        s3_review = S3ImageReview(ctx, key_prefix, known_images=character.images, hidden=hidden)
        await s3_review.send(ctx)

    ### TRAIT COMMANDS ####################################################################
    @trait.command(name="add", description="Add a trait to a character")
    async def add_trait(
        self,
        ctx: ValentinaContext,
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
            default=None,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a trait to a character."""
        character = await self._fetch_active_character(ctx)

        if not await ctx.can_manage_traits(character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to add traits to this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        title = f"Add trait: `{name.title()}` at `{value}` dots for {character.name}"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        await character.add_trait(category, name.title(), value, max_value=max_value)

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    @trait.command(name="update", description="Update the value of a trait for a character")
    async def update_trait(
        self,
        ctx: ValentinaContext,
        trait_index: Option(
            int,  # Index of the trait in character.traits
            description="Trait to update",
            required=True,
            autocomplete=select_char_trait,
            name="trait",
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
        # Fetch the active character and trait
        character = await self._fetch_active_character(ctx)

        # Guard statement: check permissions
        if not await ctx.can_manage_traits(character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to update traits on this character\nSpeak to an administrator or spend xp.",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        # Grab the CharacterTrait object
        trait = character.traits[trait_index]

        if not 0 <= new_value <= trait.max_value:
            await present_embed(
                ctx,
                title="Invalid value",
                description=f"Value must be less than or equal to {trait.max_value}",
                level="error",
                ephemeral=hidden,
            )
            return

        title = (
            f"Update `{trait.name}` from `{trait.value}` to `{new_value}` for `{character.name}`"
        )
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        trait.value = new_value
        await trait.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    @trait.command(name="delete", description="Delete a trait from a character")
    async def delete_trait(
        self,
        ctx: ValentinaContext,
        trait_index: Option(
            int,
            description="Trait to delete",
            required=True,
            name="trait",
            autocomplete=select_char_trait,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a trait from a character."""
        # Fetch the active character and trait
        character = await self._fetch_active_character(ctx)
        trait = character.traits[trait_index]

        # Guard statement: check permissions
        if not await ctx.can_manage_traits(character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to delete traits from this character",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        title = f"Delete trait `{trait.name}` from `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx,
            title,
            description="This is a destructive action that can not be undone.",
            hidden=hidden,
        )

        if not is_confirmed:
            return

        character.traits.pop(trait_index)
        await character.save()

        await trait.delete()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    ### SECTION COMMANDS ####################################################################

    @section.command(name="add", description="Add a new custom section to the character sheet")
    async def add_custom_section(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a custom section to the character sheet."""
        character = await self._fetch_active_character(ctx)

        modal = CustomSectionModal(
            title=truncate_string(f"Custom section for {character.name}", 45)
        )
        await ctx.send_modal(modal)
        await modal.wait()

        section_title = modal.section_title.strip().title()
        section_content = modal.section_content.strip()

        if section_title.replace("-", "_").replace(" ", "_").lower() in [
            x.title.replace("-", "_").replace(" ", "_").lower() for x in character.sheet_sections
        ]:
            msg = f"Custom section `{section_title}`already exists"
            raise errors.ValidationError(msg)

        character.sheet_sections.append(
            CharacterSheetSection(title=section_title, content=section_content)
        )
        await character.save()

        await ctx.post_to_audit_log(f"Add section `{section_title}` to `{character.name}`")
        await present_embed(
            ctx,
            f"Add section `{section_title}` to `{character.name}`",
            description=f"**{section_title}**\n{section_content}",
            ephemeral=hidden,
            level="success",
        )

    @section.command(name="update", description="Update a custom section")
    async def update_custom_section(
        self,
        ctx: ValentinaContext,
        input_info: Option(
            ValidCustomSection,
            description="Custom section to update",
            name="custom_section",
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
        section, index, character = input_info

        modal = CustomSectionModal(
            section_title=section.title,
            section_content=section.content,
            title=truncate_string("Edit custom section", 45),
        )
        await ctx.send_modal(modal)
        await modal.wait()

        section.title = modal.section_title.strip().title()
        section.content = modal.section_content.strip()

        character.sheet_sections[index] = section
        await character.save()

        title = f"Update section `{section.title}` for `{character.name}`"
        await ctx.post_to_audit_log(title)
        await present_embed(
            ctx,
            title=title,
            description=f"**{section.title}**\n{section.content}",
            ephemeral=hidden,
            level="success",
        )

    @section.command(name="delete", description="Delete a custom section from a character")
    async def delete_custom_section(
        self,
        ctx: ValentinaContext,
        input_info: Option(
            ValidCustomSection,
            description="Custom section to delete",
            name="custom_section",
            required=True,
            autocomplete=select_custom_section,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a custom section from a character."""
        section, index, character = input_info

        title = f"Delete section `{section.title}` from `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        character.sheet_sections.pop(index)
        await character.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    ### BIO COMMANDS ####################################################################

    @bio.command(name="update", description="Add or update a character's bio")
    async def update_bio(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update a character's bio."""
        character = await self._fetch_active_character(ctx)

        modal = BioModal(
            title=truncate_string(f"Enter the biography for {character.name}", 45),
            current_bio=character.bio,
        )
        await ctx.send_modal(modal)
        await modal.wait()
        biography = modal.bio.strip()

        character.bio = biography
        await character.save()

        await ctx.post_to_audit_log(f"Update biography for `{character.name}`")
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
        ctx: ValentinaContext,
        dob: Option(ValidYYYYMMDD, description="DOB in the format of YYYY-MM-DD", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set the DOB of a character."""
        character = await self._fetch_active_character(ctx)

        character.dob = dob
        await character.save()

        await ctx.post_to_audit_log(f"`{character.name}` DOB set to `{dob:%Y-%m-%d}`")
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
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update a character's profile."""
        character = await self._fetch_active_character(ctx)

        modal = ProfileModal(
            title=truncate_string(f"Profile for {character}", 45), character=character
        )
        await ctx.send_modal(modal)
        await modal.wait()
        if modal.confirmed:
            for k, v in modal.results.items():
                if v:
                    character.__dict__[k] = v

            await character.save()

            await ctx.post_to_audit_log(f"Update profile for `{character.name}`")
            await present_embed(
                ctx,
                title=f"Update profile for `{character.name}`",
                level="success",
                ephemeral=hidden,
            )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(CharactersCog(bot))
