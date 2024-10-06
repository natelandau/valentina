# mypy: disable-error-code="valid-type"
"""Character cog for Valentina."""

from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.constants import (
    VALID_IMAGE_EXTENSIONS,
    CharClass,
    EmbedColor,
    Emoji,
    RNGCharLevel,
)
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.characters import AddFromSheetWizard, CharGenWizard
from valentina.discord.utils.autocomplete import (
    select_any_player_character,
    select_campaign,
    select_char_class,
    select_char_trait,
    select_custom_section,
    select_trait_category,
    select_vampire_clan,
)
from valentina.discord.utils.converters import (
    ValidCampaign,
    ValidCharacterName,
    ValidCharacterObject,
    ValidCharClass,
    ValidClan,
    ValidImageURL,
    ValidTraitCategory,
    ValidTraitFromID,
    ValidYYYYMMDD,
)
from valentina.discord.utils.discord_utils import fetch_channel_object
from valentina.discord.views import (
    BioModal,
    CustomSectionModal,
    ProfileModal,
    S3ImageReview,
    auto_paginate,
    confirm_action,
    present_embed,
    show_sheet,
)
from valentina.models import AWSService, Character, CharacterSheetSection, User
from valentina.utils import errors
from valentina.utils.helpers import (
    fetch_data_from_url,
    truncate_string,
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
    admin = chars.create_subgroup("admin", "Admin commands for characters")

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
            ctx (ValentinaContext): The context of the command
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

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

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

        wizard = AddFromSheetWizard(ctx, character=character, user=user, campaign=campaign)
        await wizard.begin_chargen()

        await ctx.post_to_audit_log(f"Create player character: `{character.name}`")

    @chars.command(name="create", description="Create a new randomized character")
    async def create_character(
        self,
        ctx: ValentinaContext,
    ) -> None:
        """Create a new character from scratch."""
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        # Grab the current user and campaign experience
        user = await User.get(ctx.author.id, fetch_links=True)
        campaign_xp, _, _ = user.fetch_campaign_xp(campaign)

        # Abort if user does not have enough xp
        if campaign_xp < 10:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Not enough xp",
                description="You do not have enough xp to create a new character",
                level="error",
                ephemeral=True,
            )
            return

        # This paginator must not be hidden - Regression in pycord 2.5.0
        wizard = CharGenWizard(
            ctx, campaign=campaign, user=user, experience_level=RNGCharLevel.NEW, hidden=False
        )
        await wizard.start()

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
            Character.guild == ctx.guild.id,
            Character.type_player == True,  # noqa: E712
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

        title_prefix = "All" if scope == "all" else "Your"
        text = f"## {title_prefix} {p.plural_noun('character', len(all_characters))} on `{ctx.guild.name}`\n"
        for character in sorted(all_characters, key=lambda x: x.name):
            user = await User.get(character.user_owner, fetch_links=True)
            dead_emoji = Emoji.DEAD.value if not character.is_alive else ""

            text += f"- {dead_emoji} **{character.name}** _({character.char_class.value.name})_ `@{user.name}`\n"

        await auto_paginate(
            ctx=ctx, title="", text=text, color=EmbedColor.INFO, hidden=hidden, max_chars=900
        )

    @chars.command(name="kill", description="Kill a character")
    async def kill_character(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Kill a character."""
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character
        campaign = channel_objects.campaign

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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        character.is_alive = False
        await character.save()

        if campaign:
            await character.confirm_channel(ctx, campaign)
            await campaign.sort_channels(ctx)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @chars.command(name="rename", description="Rename a character")
    async def rename(
        self,
        ctx: ValentinaContext,
        first_name: Option(ValidCharacterName, "Character's name", required=True),
        last_name: Option(ValidCharacterName, "Character's last name", required=True),
        nickname: Option(ValidCharacterName, "Character's nickname", required=False, default=None),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Rename a character."""
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character
        campaign = channel_objects.campaign

        nick = f"'{nickname}' " if nickname else ""

        title = f"Rename `{character.name}` to `{first_name} {nick}{last_name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        character.name_first = first_name
        character.name_last = last_name
        character.name_nick = nickname
        await character.save()

        if campaign:
            await character.confirm_channel(ctx, campaign)
            await campaign.sort_channels(ctx)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
            ctx (ValentinaContext): The application context.
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

        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

        # Determine image extension and read data
        extension = file_extension if file else url.split(".")[-1].lower()
        data = await file.read() if file else await fetch_data_from_url(url)

        # Upload image and add to character
        # We upload the image prior to the confirmation step to allow us to display the image to the user.  If the user cancels the confirmation, we must delete the image from S3 and from the character object.
        image_key = await character.add_image(extension=extension, data=data)
        image_url = self.aws_svc.get_url(image_key)

        title = f"Add image to `{character.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, image=image_url, audit=True
        )
        if not is_confirmed:
            await character.delete_image(image_key)
            return

        # Update audit log and original response
        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
            ctx (ValentinaContext): The application context.
            hidden (bool): Whether the interaction should only be visible to the user initiating it.

        Returns:
            None
        """
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        await character.add_trait(category, name.title(), value, max_value=max_value)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @trait.command(name="update", description="Update the value of a trait for a character")
    async def update_trait(
        self,
        ctx: ValentinaContext,
        trait: Option(
            ValidTraitFromID,
            name="trait_one",
            description="First trait to roll",
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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        trait.value = new_value
        await trait.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @trait.command(name="delete", description="Delete a trait from a character")
    async def delete_trait(
        self,
        ctx: ValentinaContext,
        trait: Option(
            ValidTraitFromID,
            name="trait_one",
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a trait from a character."""
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description="This is a destructive action that can not be undone.",
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        character.traits.remove(trait)
        await character.save()

        await trait.delete()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        section_index: Option(
            int,
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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

        section = character.sheet_sections[section_index]

        modal = CustomSectionModal(
            section_title=section.title,
            section_content=section.content,
            title=truncate_string("Edit custom section", 45),
        )
        await ctx.send_modal(modal)
        await modal.wait()

        section.title = modal.section_title.strip().title()
        section.content = modal.section_content.strip()

        character.sheet_sections[section_index] = section
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
        section_index: Option(
            int,
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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

        section = character.sheet_sections[section_index]

        title = f"Delete section `{section.title}` from `{character.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        character.sheet_sections.pop(section_index)
        await character.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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

    ### PROFILE COMMANDS ####################################################################

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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

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
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

        modal = ProfileModal(
            title=truncate_string(f"Profile for {character.name}", 45), character=character
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

    ### ADMIN COMMANDS ####################################################################
    @admin.command(name="campaign", description="Associate character with a campaign")
    async def associate_campaign(
        self,
        ctx: ValentinaContext,
        campaign: Option(
            ValidCampaign,
            name="campaign",
            description="Campaign to associate with the character",
            required=True,
            autocomplete=select_campaign,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Associate a character with a campaign."""
        channel_objects = await fetch_channel_object(ctx, need_character=True)
        character = channel_objects.character

        title = f"Associate `{character.name}` with `{campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        await character.associate_with_campaign(ctx, campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @admin.command(name="transfer", description="Transfer one of your characters to another user")
    async def transfer_character(
        self,
        ctx: ValentinaContext,
        new_owner: Option(discord.User, description="The user to transfer the character to"),
        hidden: Option(
            bool,
            description="Make the sheet only visible to you (default false).",
            default=False,
        ),
    ) -> None:
        """Transfer one of your characters to another user."""
        channel_objects = await fetch_channel_object(ctx, need_character=True, need_campaign=True)
        character = channel_objects.character
        campaign = channel_objects.campaign

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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        current_user = await User.get(ctx.author.id, fetch_links=True)
        new_user = await User.get(new_owner.id, fetch_links=True)

        await current_user.remove_character(character)
        new_user.characters.append(character)
        await new_user.save()

        character.user_owner = new_owner.id
        await character.save()

        await character.update_channel_permissions(ctx, campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(CharactersCog(bot))
