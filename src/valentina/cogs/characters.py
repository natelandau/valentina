# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.character.traits import add_trait
from valentina.character.wizard import CharGenWizard
from valentina.models.bot import Valentina
from valentina.models.database import CustomTrait, TraitValue, time_now
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterName,
    ValidCharacterObject,
    ValidCharTrait,
    ValidClan,
    ValidCustomSection,
    ValidCustomTrait,
    ValidTraitCategory,
    ValidYYYYMMDD,
)
from valentina.utils.errors import SectionExistsError
from valentina.utils.options import (
    select_char_class,
    select_char_trait,
    select_character,
    select_custom_section,
    select_custom_trait,
    select_trait_category,
    select_vampire_clan,
)
from valentina.views import (
    BioModal,
    ConfirmCancelButtons,
    CustomSectionModal,
    ProfileModal,
    present_embed,
)
from valentina.views.character_sheet import show_sheet

# TODO: Add a way to mark a character as dead


class Characters(commands.Cog, name="Character"):
    """Create, manage, update, and claim characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        logger.exception(error)

        command_name = ""
        if ctx.command.parent.name:
            command_name = f"{ctx.command.parent.name} "
        command_name += ctx.command.name

        await present_embed(
            ctx,
            title=f"Error running `{command_name}` command",
            description=str(error),
            level="error",
            ephemeral=True,
            delete_after=15,
        )

    chars = discord.SlashCommandGroup("character", "Work with characters")
    update = chars.create_subgroup("update", "Update existing characters")
    add = chars.create_subgroup("add", "Add custom information to existing characters")
    delete = chars.create_subgroup("delete", "Delete information from existing characters")

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
        self.bot.user_svc.fetch_user(ctx)

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
        character = self.bot.char_svc.create_character(
            ctx,
            first_name=first_name,
            last_name=last_name,
            nickname=nickname,
            char_class=char_class,
            clan=vampire_clan,
        )
        self.bot.char_svc.update_traits_by_id(ctx, character, trait_values_from_chargen)
        logger.info(f"CHARACTER: Create character [{character.id}] {character.name}")

    @chars.command(name="sheet", description="View a character sheet")
    async def view_character_sheet(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_character,
            required=True,
        ),
    ) -> None:
        """Displays a character sheet in the channel."""
        if self.bot.char_svc.is_char_claimed(ctx.guild.id, character.id):
            user_id_num = self.bot.char_svc.fetch_user_of_character(ctx.guild.id, character.id)
            claimed_by = self.bot.get_user(user_id_num)
        else:
            claimed_by = None

        await show_sheet(ctx, character=character, claimed_by=claimed_by)

    @chars.command(name="claim", description="Claim a character")
    async def claim_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to claim",
            autocomplete=select_character,
            required=True,
            name="character",
        ),
    ) -> None:
        """Claim a character to your user. This will allow you to roll without specifying traits, edit the character, and more."""
        self.bot.char_svc.add_claim(ctx.guild.id, character.id, ctx.user.id)

        logger.info(f"CLAIM: {character.name} claimed by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title="Character Claimed",
            description=f"**{character.name}** has been claimed by **{ctx.author.display_name}**",
            level="success",
        )

    @chars.command(name="unclaim", description="Unclaim a character")
    async def unclaim_character(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """Unclaim currently claimed character. This will allow you to claim a new character."""
        if self.bot.char_svc.user_has_claim(ctx):
            character = self.bot.char_svc.fetch_claim(ctx)
            self.bot.char_svc.remove_claim(ctx)
            await present_embed(
                ctx=ctx,
                title="Character Unclaimed",
                description=f"**{character.name}** unclaimed by **{ctx.author.display_name}**",
                level="success",
            )
        else:
            await present_embed(
                ctx=ctx,
                title="You have no character claimed",
                description="To claim a character, use `/character claim`.",
                level="error",
                ephemeral=True,
            )

    @chars.command(name="list", description="List all characters")
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all characters."""
        characters = self.bot.char_svc.fetch_all_characters(ctx.guild.id)
        if len(characters) == 0:
            await present_embed(
                ctx,
                title="No Characters",
                description="There are no characters.\nCreate one with `/character create`",
                level="error",
            )
            return

        fields = []
        plural = "s" if len(characters) > 1 else ""
        description = f"**{len(characters)}** character{plural} on this server\n\u200b"

        for character in sorted(characters, key=lambda x: x.name):
            user_id = self.bot.char_svc.fetch_user_of_character(ctx.guild.id, character.id)
            user = self.bot.get_user(user_id).display_name if user_id else ""
            fields.append(
                (character.name, f"Class: {character.char_class.name}\nClaimed by: {user}")
            )

        await present_embed(
            ctx=ctx,
            title="List of characters",
            description=description,
            fields=fields,
            inline_fields=False,
            level="info",
        )

    ### ADD COMMANDS ####################################################################

    @add.command(name="date_of_birth", description="Set the DOB of a character")
    async def date_of_birth(
        self,
        ctx: discord.ApplicationContext,
        dob: Option(ValidYYYYMMDD, description="DOB in the format of YYYY-MM-DD", required=True),
    ) -> None:
        """Set the age of a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        self.bot.char_svc.update_character(ctx, character.id, date_of_birth=dob)
        logger.debug(f"CHARACTER: {character} dob updated by {ctx.author.name}.")

        await present_embed(
            ctx,
            title="Date of Birth Updated",
            description=f"{character} born on {dob:%Y-%m-%d}",
            level="success",
            ephemeral=True,
            log=True,
        )

    @add.command(name="trait", description="Add a custom trait to a character")
    async def add_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(str, "The new trait to add.", required=True),
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
    ) -> None:
        """Add a custom trait to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)
        await add_trait(
            ctx=ctx,
            character=character,
            trait_name=trait,
            category=category,
            trait_value=value,
            max_value=max_value,
            trait_description=description,
        )

    @add.command(name="custom_section", description="Add a custom section to the character sheet")
    async def add_custom_section(self, ctx: discord.ApplicationContext) -> None:
        """Add a custom section to the character sheet."""
        character = self.bot.char_svc.fetch_claim(ctx)
        modal = CustomSectionModal(title=f"Custom section for {character.name}")
        await ctx.send_modal(modal)
        await modal.wait()
        section_title = modal.section_title.strip().title()
        section_description = modal.section_description.strip()

        existing_sections = character.custom_sections
        if section_title.replace("-", "_").replace(" ", "_").lower() in [
            x.title.replace("-", "_").replace(" ", "_").lower() for x in existing_sections
        ]:
            raise SectionExistsError
        self.bot.char_svc.add_custom_section(character, section_title, section_description)
        await present_embed(
            ctx,
            title="Custom Section Added",
            fields=[
                ("Character", character.name),
                ("Section", section_title),
                ("Content", section_description),
            ],
            ephemeral=True,
            inline_fields=True,
            level="success",
            log=True,
        )

    ### UPDATE COMMANDS ####################################################################
    @update.command(name="bio", description="Add or update a character's bio")
    async def update_bio(self, ctx: discord.ApplicationContext) -> None:
        """Update a character's bio."""
        character = self.bot.char_svc.fetch_claim(ctx)

        modal = BioModal(
            title=f"Enter the biography for {character.name}", current_bio=character.bio
        )
        await ctx.send_modal(modal)
        await modal.wait()
        biography = modal.bio.strip()

        self.bot.char_svc.update_character(ctx, character.id, bio=biography)
        logger.info(f"BIO: {character} bio updated by {ctx.author.name}.")

        await present_embed(
            ctx,
            title="Biography Updated",
            level="success",
            ephemeral=True,
            log=True,
            inline_fields=True,
            fields=[("Character", character.name), ("Biography", biography)],
        )

    @update.command(name="custom_section", description="Update a custom section")
    async def update_custom_section(
        self,
        ctx: discord.ApplicationContext,
        custom_section: Option(
            ValidCustomSection,
            description="Custom section to update",
            required=True,
            autocomplete=select_custom_section,
        ),
    ) -> None:
        """Update a custom section."""
        character = self.bot.char_svc.fetch_claim(ctx)

        modal = CustomSectionModal(
            section_title=custom_section.title,
            section_description=custom_section.description,
            title=f"Custom section for {character.name}",
        )
        await ctx.send_modal(modal)
        await modal.wait()
        section_title = modal.section_title.strip().title()
        section_description = modal.section_description.strip()

        custom_section.title = section_title
        custom_section.description = section_description
        custom_section.save()
        self.bot.char_service.purge_cache(ctx)

        await present_embed(
            ctx,
            title="Custom Section Updated",
            fields=[
                ("Character", character.name),
                ("Section", section_title),
                ("Content", section_description),
            ],
            ephemeral=True,
            inline_fields=True,
            level="success",
            log=True,
        )

    @chars.command(name="profile", description="Update a character's profile")
    async def update_profile(self, ctx: discord.ApplicationContext) -> None:
        """Update a character's profile."""
        character = self.bot.char_svc.fetch_claim(ctx)

        modal = ProfileModal(title=f"Profile for {character}", character=character)
        await ctx.send_modal(modal)
        await modal.wait()
        if modal.confirmed:
            for k, v in modal.results.items():
                if v:
                    character.__setattr__(k, v)

            character.save()
            self.bot.char_svc.purge_cache(ctx)

            await present_embed(
                ctx,
                title="Profile Updated",
                log=True,
                level="success",
                ephemeral=True,
            )

    @update.command(name="trait", description="Update the value of a trait for a character")
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
    ) -> None:
        """Update the value of a trait."""
        character = self.bot.char_svc.fetch_claim(ctx)

        if not self.bot.user_svc.has_trait_permissions(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to update traits on this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        old_value = character.trait_value(trait)

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title=f"Update {trait.name}",
            fields=[
                ("Old Value", str(old_value)),
                ("New Value", new_value),
            ],
            inline_fields=True,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Update Cancelled",
                    description=f"**{trait.name}** will not be updated.",
                    color=discord.Color.red(),
                )
            )
            return

        if isinstance(trait, CustomTrait):
            trait.value = new_value
            trait.modified = time_now()
            trait.save()
        else:
            TraitValue.update(value=new_value, modified=time_now()).where(
                TraitValue.character == character, TraitValue.trait == trait
            ).execute()

        character.modified = time_now()
        character.save()

        await msg.delete_original_response()
        await present_embed(
            ctx=ctx,
            title="Trait value updated",
            description=f"**{trait.name}** updated from **{old_value}** to **{new_value}** on **{character.name}**",
            level="success",
            ephemeral=True,
            log=True,
        )

    ### DELETE COMMANDS ####################################################################
    @delete.command(name="trait", description="Delete a custom trait from a character")
    async def delete_custom_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            ValidCustomTrait,
            description="Trait to delete",
            required=True,
            autocomplete=select_custom_trait,
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        character = self.bot.char_svc.fetch_claim(ctx)
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete Trait",
            description=f"Confirm deleting {trait.name}",
            ephemeral=True,
            view=view,
            level="info",
        )
        await view.wait()
        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Delete Cancelled",
                    description=f"**{trait.name}** will not be deleted.",
                    color=discord.Color.red(),
                )
            )
            return

        if view.confirmed:
            saved_trait_name = trait.name
            trait.delete_instance()
            await msg.delete_original_response()
            await present_embed(
                ctx=ctx,
                title="Deleted Trait",
                fields=[("Character", character.name), ("Trait", saved_trait_name)],
                inline_fields=True,
                level="success",
                log=True,
                ephemeral=True,
            )

    @delete.command(name="custom_section", description="Delete a custom section from a character")
    async def delete_custom_section(
        self,
        ctx: discord.ApplicationContext,
        custom_section: Option(
            ValidCustomSection,
            description="Custom section to delete",
            required=True,
            autocomplete=select_custom_section,
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        character = self.bot.char_svc.fetch_claim(ctx)
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete Custom Section",
            description=f"Confirm deleting {custom_section.title}",
            ephemeral=True,
            view=view,
            level="info",
        )
        await view.wait()
        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Delete Cancelled",
                    description=f"**{custom_section.title}** will not be deleted.",
                    color=discord.Color.red(),
                )
            )
            return

        saved_section_title = custom_section.title
        custom_section.delete_instance()

        await present_embed(
            ctx=ctx,
            title="Deleted Custom Section",
            fields=[("Character", character.name), ("Section", saved_section_title)],
            level="success",
            log=True,
            ephemeral=True,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
