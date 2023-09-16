# mypy: disable-error-code="valid-type"
"""Commands for the storyteller."""
import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from loguru import logger
from peewee import fn

from valentina.constants import COOL_POINT_VALUE, DEFAULT_DIFFICULTY, DiceType, EmbedColor
from valentina.models.bot import Valentina
from valentina.models.db_tables import VampireClan
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterName,
    ValidCharacterObject,
    ValidClan,
    ValidTraitCategory,
)
from valentina.utils.helpers import fetch_random_name
from valentina.utils.options import (
    select_any_player_character,
    select_char_class,
    select_country,
    select_player_character,
    select_storyteller_character,
    select_storyteller_trait,
    select_storyteller_trait_two,
    select_trait_category,
    select_vampire_clan,
)
from valentina.utils.perform_roll import perform_roll
from valentina.utils.storyteller import storyteller_character_traits
from valentina.views import (
    CharGenWizard,
    ConfirmCancelButtons,
    confirm_action,
    present_embed,
    sheet_embed,
    show_sheet,
)

p = inflect.engine()


class StoryTeller(commands.Cog):
    """Commands for the storyteller."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    storyteller = discord.SlashCommandGroup(
        "storyteller",
        "Commands for the storyteller",
        checks=[commands.has_any_role("Storyteller", "Admin").predicate],  # type: ignore [attr-defined]
    )
    character = storyteller.create_subgroup(
        "character",
        "Work with storyteller characters",
        checks=[commands.has_any_role("Storyteller", "Admin").predicate],  # type: ignore [attr-defined]
    )
    player = storyteller.create_subgroup(
        "player",
        "Work with player characters",
        checks=[commands.has_any_role("Storyteller", "Admin").predicate],  # type: ignore [attr-defined]
    )
    roll = storyteller.create_subgroup(
        "roll",
        "Roll dice for storyteller characters",
        checks=[commands.has_any_role("Storyteller", "Admin").predicate],  # type: ignore [attr-defined]
    )

    ### CHARACTER COMMANDS ####################################################################
    @character.command(name="create_full", description="Create a full npc character")
    async def create_story_char(
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
        """Create a new storyteller character."""
        # Ensure the user is in the database
        self.bot.user_svc.fetch_user(ctx)

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
            "storyteller_character": True,
        }

        character = self.bot.char_svc.update_or_add(
            ctx,
            data=data,
            char_class=char_class,
            clan=vampire_clan,
        )

        for trait, value in trait_values_from_chargen:
            character.set_trait_value(trait, value)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Created storyteller character: `{character.full_name}` as a `{char_class.name}`"
        )
        logger.info(f"CHARACTER: Create character {character}")

    @character.command(name="create_rng", description="Create a random new npc character")
    async def create_rng_char(
        self,
        ctx: discord.ApplicationContext,
        gender: Option(
            str,
            name="gender",
            description="The character's gender",
            choices=["male", "female"],
            required=True,
        ),
        char_class: Option(
            ValidCharacterClass,
            name="char_class",
            description="The character's class",
            autocomplete=select_char_class,
            required=True,
        ),
        level: Option(
            str,
            name="level",
            description="The character's level",
            required=True,
            choices=[
                "Weakling",
                "Average",
                "Strong",
                "Super",
            ],
        ),
        specialty: Option(
            str,
            name="specialty",
            description="The character's specialty",
            required=True,
            choices=["No Specialty", "Fighter", "Thinker", "Leader"],
            default="No Specialty",
        ),
        name_type: Option(
            str,
            name="name_type",
            description="The character's name type",
            autocomplete=select_country,
            default="us",
        ),
        vampire_clan: Option(
            ValidClan,
            name="vampire_clan",
            description="The character's clan (only for vampires)",
            autocomplete=select_vampire_clan,
            required=False,
            default=None,
        ),
    ) -> None:
        """Create a new storyteller character."""
        first_name, last_name = await fetch_random_name(gender=gender, country=name_type)

        if char_class.name.lower() == "vampire" and not vampire_clan:
            vampire_clan = VampireClan.select().order_by(fn.Random()).limit(1)[0]

        data = {
            "first_name": first_name,
            "last_name": last_name,
            "nickname": char_class.name,
            "storyteller_character": True,
            "player_character": False,
        }

        character = self.bot.char_svc.update_or_add(
            ctx,
            data=data,
            char_class=char_class,
            clan=vampire_clan,
        )

        fetched_traits = self.bot.trait_svc.fetch_all_class_traits(char_class.name)
        trait_values = storyteller_character_traits(
            fetched_traits,
            level=level,
            specialty=specialty,
            clan=vampire_clan.name if vampire_clan else None,
        )

        for trait, value in trait_values:
            character.set_trait_value(trait, value)

        # Confirm character creation
        view = ConfirmCancelButtons(ctx.author)
        embed = await sheet_embed(
            ctx, character, title=f"Confirm creation of {character.full_name}"
        )
        msg = await ctx.respond(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if not view.confirmed:
            character.delete_instance(delete_nullable=True, recursive=True)

            await msg.edit_original_response(  # type: ignore [union-attr]
                embed=discord.Embed(
                    title=f"{character.full_name} discarded",
                    color=EmbedColor.WARNING.value,
                ),
            )
            return

        await msg.edit_original_response(  # type: ignore [union-attr]
            embed=discord.Embed(
                title=f"{character.full_name} saved",
                color=EmbedColor.SUCCESS.value,
            ),
        )
        await self.bot.guild_svc.send_to_audit_log(
            ctx,
            discord.Embed(
                title="Storyteller character created", description=f"Created {character.full_name}"
            ),
        )

    @character.command(name="list", description="List all characters")
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all storyteller characters."""
        characters = self.bot.char_svc.fetch_all_storyteller_characters(ctx)

        if len(characters) == 0:
            await present_embed(
                ctx,
                title="No Storyteller Characters",
                description="There are no characters.\nCreate one with `/storyteller new_character`",
                level="error",
                ephemeral=True,
            )
            return

        fields = []
        plural = "s" if len(characters) > 1 else ""
        description = f"**{len(characters)}** character{plural} on this server\n\u200b"

        for character in sorted(characters, key=lambda x: x.name):
            fields.append(
                (
                    character.full_name,
                    f"Class: `{character.char_class.name}`",
                )
            )

        await present_embed(
            ctx=ctx,
            title="List of storyteller characters",
            description=description,
            fields=fields,
            inline_fields=False,
            level="info",
        )

    @character.command(name="update", description="Update a storyteller character")
    async def update_storyteller_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to update",
            autocomplete=select_storyteller_character,
            required=True,
        ),
        trait: Option(
            str,
            description="Trait to update",
            required=True,
            autocomplete=select_storyteller_trait,
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
        """Update the value of a trait for a storyteller or player character."""
        # Get trait object from name
        found_trait = False
        for t in character.traits_list:
            if trait.lower() == t.name.lower():
                found_trait = True
                trait = t
                break

        if not found_trait:
            await present_embed(
                ctx,
                title="Trait not found",
                description=f"Trait `{trait}` not found for character `{character.full_name}`",
                level="error",
                ephemeral=True,
            )
            return

        old_value = character.get_trait_value(trait)

        title = f"Update `{trait.name}` for `{character.name}` from `{old_value}` to `{new_value}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        character.set_trait_value(trait, new_value)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @character.command(name="sheet", description="View a character sheet")
    async def view_character_sheet(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_storyteller_character,
            required=True,
        ),
    ) -> None:
        """View a character sheet for a storyteller character."""
        await show_sheet(ctx, character=character)

    @character.command(name="delete", description="Delete a storyteller character")
    async def delete_storyteller_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to delete",
            autocomplete=select_storyteller_character,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a storyteller character."""
        title = f"Delete storyteller character `{character.full_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        character.delete_instance(delete_nullable=True, recursive=True)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @character.command(name="add_trait", description="Add a trait to a storyteller character")
    async def add_custom_trait(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to delete",
            autocomplete=select_storyteller_character,
            required=True,
        ),
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

    ### PLAYER COMMANDS ####################################################################

    @player.command(
        name="transfer_character", description="Transfer a character from one owner to another."
    )
    async def transfer_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to transfer",
            autocomplete=select_any_player_character,
            required=True,
        ),
        new_owner: Option(discord.User, description="The user to transfer the character to"),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Update the value of a trait for a storyteller or player character."""
        title = f"Transfer `{character.full_name}` from `{character.owned_by.username}` to `{new_owner.display_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.user_svc.transfer_character_owner(ctx, character, new_owner)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @player.command(name="update", description="Update a player character")
    async def update_player_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to update",
            autocomplete=select_player_character,
            required=True,
        ),
        trait: Option(
            str,
            description="Trait to update",
            required=True,
            autocomplete=select_storyteller_trait,
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
        """Update the value of a trait for a storyteller or player character."""
        # Get trait object from name
        for t in character.traits_list:
            if trait.lower() == t.name.lower():
                trait = t
                break

        old_value = character.get_trait_value(trait)

        title = f"Update `{trait.name}` for `{character.name}` from `{old_value}` to `{new_value}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        character.set_trait_value(trait, new_value)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @player.command(name="grant_xp", description="Grant xp to a player character")
    async def grant_xp(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to grant xp to",
            autocomplete=select_player_character,
            required=True,
        ),
        xp: Option(int, description="The amount of xp to grant", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Grant xp to a player character."""
        current_xp = character.data.get("experience", 0)
        current_xp_total = character.data.get("experience_total", 0)
        new_xp = current_xp + xp
        new_xp_total = current_xp_total + xp

        title = f"Grant `{xp}` xp to `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "experience": new_xp,
                "experience_total": new_xp_total,
            },
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @player.command(name="grant_cp", description="Grant a cool point to a player character")
    async def grant_cp(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to grant a cp to",
            autocomplete=select_player_character,
            required=True,
        ),
        cp: Option(int, description="The number of cool points to grant", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Grant a cool point to a player character."""
        current_cp = character.data.get("cool_points_total", 0)
        current_xp = character.data.get("experience", 0)
        current_xp_total = character.data.get("experience_total", 0)

        xp_amount = cp * COOL_POINT_VALUE

        new_xp = current_xp + xp_amount
        new_xp_total = current_xp_total + xp_amount
        new_cp_total = current_cp + cp

        title = f"Grant `{cp}` cool {p.plural_noun('member', cp)} (`{xp_amount}` xp) to `{character.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "experience": new_xp,
                "experience_total": new_xp_total,
                "cool_points_total": new_cp_total,
            },
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    ### ROLL COMMANDS ####################################################################

    @roll.command(name="roll_traits", description="Roll traits for a character")
    async def roll_traits(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to roll traits for",
            autocomplete=select_storyteller_character,
            required=True,
        ),
        trait_one: Option(
            str,
            description="First trait to roll",
            required=True,
            autocomplete=select_storyteller_trait,
        ),
        trait_two: Option(
            str,
            description="Second trait to roll",
            required=True,
            autocomplete=select_storyteller_trait_two,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=DEFAULT_DIFFICULTY,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Roll traits for a storyteller character."""
        # Get trait objects from names
        for t in character.traits_list:
            if trait_one.lower() == t.name.lower():
                trait_one = t
                break

        for t in character.traits_list:
            if trait_two.lower() == t.name.lower():
                trait_two = t
                break

        trait_one_value = character.get_trait_value(trait_one)
        trait_two_value = character.get_trait_value(trait_two)

        pool = trait_one_value + trait_two_value

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            hidden=hidden,
            trait_one=trait_one,
            trait_one_value=trait_one_value,
            trait_two=trait_two,
            trait_two_value=trait_two_value,
            character=character,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(StoryTeller(bot))
