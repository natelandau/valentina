# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, char_svc
from valentina.character.create import create_character
from valentina.character.traits import add_trait
from valentina.character.view_sheet import show_sheet
from valentina.character.views import BioModal, CustomSectionModal
from valentina.models.constants import MAX_OPTION_LIST_SIZE, CharClass, TraitCategory
from valentina.utils.errors import (
    CharacterClaimedError,
    NoClaimError,
    SectionExistsError,
    TraitNotFoundError,
    UserHasClaimError,
)
from valentina.utils.helpers import normalize_to_db_row
from valentina.utils.options import select_character
from valentina.views import ConfirmCancelButtons, present_embed

possible_classes = sorted([char_class.value for char_class in CharClass])

# TODO: Add a way to mark a character as dead


class Characters(commands.Cog, name="Character"):
    """Create, manage, update, and claim characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def __trait_autocomplete(self, ctx: discord.AutocompleteContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            return ["No character claimed"]

        traits = []
        for trait in char_svc.fetch_all_character_traits(character, flat_list=True):
            if trait.lower().startswith(ctx.options["trait"].lower()):
                traits.append(trait)
            if len(traits) >= MAX_OPTION_LIST_SIZE:
                break
        return traits

    async def __custom_section_autocomplete(self, ctx: discord.AutocompleteContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            return ["No character claimed"]

        sections = []
        for section in char_svc.fetch_char_custom_sections(ctx, character):
            if section.title.lower().startswith(ctx.options["custom_section"].lower()):
                sections.append(section.title)
            if len(sections) >= MAX_OPTION_LIST_SIZE:
                break

        return sections

    chars = discord.SlashCommandGroup("character", "Work with characters")
    update = chars.create_subgroup("update", "Update existing characters")
    add = chars.create_subgroup("add", "Add custom information to existing characters")
    delete = chars.create_subgroup("delete", "Delete information from existing characters")

    @chars.command(name="create", description="Create a new character")
    @logger.catch
    async def create_character(
        self,
        ctx: discord.ApplicationContext,
        quick_char: Option(
            str,
            name="quick",
            description="Create a character with only essential traits? (Defaults to False)",
            choices=["True", "False"],
            required=True,
        ),
        char_class: Option(
            str,
            name="class",
            description="The character's class",
            choices=[char_class.value for char_class in CharClass],
            required=True,
        ),
        first_name: Option(str, "The character's name", required=True),
        last_name: Option(str, "The character's last name", required=True),
        nickname: Option(str, "The character's nickname", required=False, default=None),
    ) -> None:
        """Create a new character.

        Args:
            char_class (CharClass): The character's class
            ctx (discord.ApplicationContext): The context of the command
            first_name (str): The character's first name
            last_name (str, optional): The character's last name. Defaults to None.
            nickname (str, optional): The character's nickname. Defaults to None.
            quick_char (bool, optional): Create a character with only essential traits? (Defaults to False).
        """
        q_char = quick_char == "True"
        await create_character(
            ctx,
            quick_char=q_char,
            char_class=char_class,
            first_name=first_name,
            last_name=last_name,
            nickname=nickname,
        )

    @chars.command(name="sheet", description="View a character sheet")
    @logger.catch
    async def view_character_sheet(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            int,
            description="The character to view",
            autocomplete=select_character,
            required=True,
        ),
    ) -> None:
        """Displays a character sheet in the channel."""
        char_db_id = int(character)
        character = char_svc.fetch_by_id(ctx.guild.id, char_db_id)

        if char_svc.is_char_claimed(ctx.guild.id, char_db_id):
            user_id_num = char_svc.fetch_user_of_character(ctx.guild.id, character.id)
            claimed_by = self.bot.get_user(user_id_num)
        else:
            claimed_by = None

        await show_sheet(ctx, character=character, claimed_by=claimed_by)

    @chars.command(name="claim", description="Claim a character")
    @logger.catch
    async def claim_character(
        self,
        ctx: discord.ApplicationContext,
        char_id: Option(
            int,
            description="The character to claim",
            autocomplete=select_character,
            required=True,
            name="character",
        ),
    ) -> None:
        """Claim a character to your user. This will allow you to roll without specifying traits, edit the character, and more."""
        character = char_svc.fetch_by_id(ctx.guild.id, char_id)

        try:
            char_svc.add_claim(ctx.guild.id, char_id, ctx.user.id)
            logger.info(f"CLAIM: {character.name} claimed by {ctx.author.name}")
            await present_embed(
                ctx=ctx,
                title="Character Claimed",
                description=f"**{character.name}** has been claimed by {ctx.author.mention}\n\nTo unclaim this character, use `/character unclaim`",
                level="success",
            )
        except CharacterClaimedError:
            await present_embed(
                ctx=ctx,
                title=f"Error: {character.name} already claimed.",
                description=f"{character.name} is already claimed by another user.\nTo unclaim this character, use `/character unclaim`.",
                level="error",
            )
        except UserHasClaimError:
            claimed_char = char_svc.fetch_claim(ctx)
            await present_embed(
                ctx=ctx,
                title="ERROR: You already have a character claimed",
                description=f"You have already claimed **{claimed_char.name}**.\nTo unclaim this character, use `/character unclaim`.",
                level="error",
            )

    @chars.command(name="unclaim", description="Unclaim a character")
    @logger.catch
    async def unclaim_character(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """Unclaim currently claimed character. This will allow you to claim a new character."""
        if char_svc.user_has_claim(ctx):
            character = char_svc.fetch_claim(ctx)
            char_svc.remove_claim(ctx)
            await present_embed(
                ctx=ctx,
                title="Character Unclaimed",
                description=f"**{character.name}** unclaimed by {ctx.author.mention}\n\nTo claim a new character, use `/character claim`.",
                level="success",
            )
        else:
            await present_embed(
                ctx=ctx,
                title="You have no character claimed",
                description="To claim a character, use `/character claim`.",
                level="error",
            )

    @chars.command(name="list", description="List all characters")
    @logger.catch
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all characters."""
        characters = char_svc.fetch_all_characters(ctx.guild.id)
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
            user_id = char_svc.fetch_user_of_character(ctx.guild.id, character.id)
            user = self.bot.get_user(user_id).mention if user_id else ""
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

    @add.command(name="trait", description="Add a custom trait to a character")
    @logger.catch
    async def add_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(str, "The new trait to add.", required=True),
        category: Option(
            str,
            "The category to add the trait to",
            required=True,
            choices=sorted([x.value for x in TraitCategory]),
        ),
        value: Option(int, "The value of the trait", required=True, min_value=1, max_value=20),
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
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed.",
                description="You must claim a character before you can add a trait.\nTo claim a character, use `/character claim`.",
                level="error",
            )
            return
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
    @logger.catch
    async def add_custom_section(self, ctx: discord.ApplicationContext) -> None:
        """Add a custom section to the character sheet."""
        try:
            character = char_svc.fetch_claim(ctx)
            modal = CustomSectionModal(title=f"Custom section for {character.name}")
            await ctx.send_modal(modal)
            await modal.wait()
            section_title = modal.section_title.strip().title()
            section_description = modal.section_description.strip()

            existing_sections = char_svc.fetch_char_custom_sections(ctx, character)
            if normalize_to_db_row(section_title) in [
                normalize_to_db_row(x.title) for x in existing_sections
            ]:
                raise SectionExistsError
            char_svc.update_char_custom_section(ctx, character, section_title, section_description)

        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed.",
                description="You must claim a character before you can add a custom section.\nTo claim a character, use `/character claim`.",
                level="error",
                ephemeral=True,
            )
            return
        except SectionExistsError:
            await present_embed(
                ctx=ctx,
                title="Error: Section already exists",
                description="A section with that name already exists.",
                level="error",
                ephemeral=True,
            )
            return

    ### UPDATE COMMANDS ####################################################################
    @update.command(name="bio", description="Update a character's bio")
    @logger.catch
    async def update_bio(self, ctx: discord.ApplicationContext) -> None:
        """Update a character's bio."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed.",
                description="You must claim a character before you can update its bio.\nTo claim a character, use `/character claim`.",
                level="error",
            )
            return

        modal = BioModal(
            title=f"Enter the biography for {character.name}", current_bio=character.bio
        )
        await ctx.send_modal(modal)
        await modal.wait()
        biography = modal.bio.strip()

        char_svc.update_char(ctx.guild.id, character.id, bio=biography)
        logger.info(f"BIO: {character.name} bio updated by {ctx.author.name}.")

    @update.command(name="trait", description="Update a trait for a character")
    @logger.catch
    async def update_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            str, description="Trait to update", required=True, autocomplete=__trait_autocomplete
        ),
        new_value: Option(
            int, description="New value for the trait", required=True, min_value=1, max_value=20
        ),
    ) -> None:
        """Update the value of a trait."""
        try:
            character = char_svc.fetch_claim(ctx)

            old_value = char_svc.fetch_trait_value(ctx, character=character, trait=trait)

            view = ConfirmCancelButtons(ctx.author)
            await present_embed(
                ctx,
                title=f"Update {trait}",
                description=f"Confirm updating {trait}",
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
            if view.confirmed and char_svc.update_trait_value(
                guild_id=ctx.guild.id, character=character, trait_name=trait, new_value=new_value
            ):
                await present_embed(
                    ctx=ctx,
                    title=f"{character.name} {trait} updated",
                    description=f"**{trait}** updated to **{new_value}**.",
                    level="success",
                    fields=[("Old Value", str(old_value)), ("New Value", new_value)],
                    inline_fields=True,
                    footer=f"Updated by {ctx.author.name}",
                    ephemeral=False,
                )
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed",
                description="You must claim a character before you can update its bio.\nTo claim a character, use `/character claim`.",
                level="error",
            )
            return
        except TraitNotFoundError:
            await present_embed(
                ctx=ctx,
                title="Error: Trait not found",
                description=f"{character.name} does not have trait: **{trait}**",
                level="error",
            )
            return

    ### DELETE COMMANDS ####################################################################
    @delete.command(name="trait", description="Delete a custom trait from a character")
    @logger.catch
    async def delete_trait(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            str, description="Trait to delete", required=True, autocomplete=__trait_autocomplete
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        # TODO: Add ability to delete a custom trait from a character
        pass

    @delete.command(name="custom_section", description="Delete a custom section from a character")
    @logger.catch
    async def delete_custom_section(
        self,
        ctx: discord.ApplicationContext,
        custom_section: Option(
            str,
            description="Custom section to delete",
            required=True,
            autocomplete=__custom_section_autocomplete,
        ),
    ) -> None:
        """Delete a custom trait from a character."""
        try:
            character = char_svc.fetch_claim(ctx)
            char_svc.delete_custom_section(ctx, character, custom_section)
            await present_embed(
                ctx=ctx,
                title=f"Deleted {custom_section}",
                description=f"**{custom_section}** has been deleted.",
                level="success",
                ephemeral=False,
            )

        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed.",
                description="You must claim a character before you can add a custom section.\nTo claim a character, use `/character claim`.",
                level="error",
                ephemeral=True,
            )
            return
        except SectionExistsError:
            await present_embed(
                ctx=ctx,
                title="Error: Section already exists",
                description="A section with that name already exists.",
                level="error",
                ephemeral=True,
            )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
