# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, char_svc, user_svc
from valentina.character.create import create_character
from valentina.character.view_sheet import show_sheet
from valentina.character.views import BioModal
from valentina.models.constants import CharClass
from valentina.utils.errors import CharacterClaimedError, NoClaimError, UserHasClaimError
from valentina.utils.options import select_character
from valentina.views.embeds import present_embed

possible_classes = [char_class.value for char_class in CharClass]


class Characters(commands.Cog, name="Character Management"):
    """Commands for characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    chars = discord.SlashCommandGroup("character", "Work with characters")
    update = chars.create_subgroup("update", "Update existing characters")

    @chars.command(name="create", description="Create a new character.")
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

    @chars.command(name="sheet", description="View a character sheet.")
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
        await show_sheet(ctx, character)

    @chars.command(name="claim", description="Claim a character.")
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
        if not user_svc.is_cached(ctx.guild.id, ctx.user.id) and not user_svc.is_in_db(
            ctx.guild.id, ctx.user.id
        ):
            user_svc.create(ctx.guild.id, ctx.user)

        character = char_svc.fetch_by_id(ctx.guild.id, char_id)

        try:
            char_svc.add_claim(ctx.guild.id, char_id, ctx.user.id)
            logger.info(f"CLAIM: {character.name} claimed by {ctx.author.name}.")
            await present_embed(
                ctx=ctx,
                title=f"{character.first_name} claimed.",
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
            claimed_char = char_svc.fetch_claim(ctx.guild.id, ctx.user.id)
            await present_embed(
                ctx=ctx,
                title="ERROR: You already have a character claimed",
                description=f"You have already claimed **{claimed_char.name}**.\nTo unclaim this character, use `/character unclaim`.",
                level="error",
            )

    @chars.command(name="list", description="List all characters.")
    @logger.catch
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all characters."""
        characters = char_svc.fetch_all(ctx.guild.id)
        description = "```[ID ] NAME                                CLASS\n"
        description += "--------------------------------------------------------\n"
        description += "\n".join(
            [
                f"[{character.id:<3}] {character.name.title():35} {character.char_class.name:11}"
                for character in characters
            ]
        )
        description += "```"

        await present_embed(ctx=ctx, title="Characters", description=description)

    ### UPDATE COMMANDS ####################################################################
    @update.command(name="bio", description="Update a character's bio.")
    @logger.catch
    async def update_bio(self, ctx: discord.ApplicationContext) -> None:
        """Update a character's bio."""
        try:
            character = char_svc.fetch_claim(ctx.guild.id, ctx.user.id)
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
        biography = modal.bio

        char_svc.update_char(ctx.guild.id, character.id, bio=biography)
        logger.info(f"BIO: {character.name} bio updated by {ctx.author.name}.")


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
