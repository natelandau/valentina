# mypy: disable-error-code="valid-type"
"""Commands for the storyteller."""
import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from peewee import fn

from valentina.models.bot import Valentina
from valentina.models.constants import COOL_POINT_VALUE, DEFAULT_DIFFICULTY, DiceType, EmbedColor
from valentina.models.db_tables import VampireClan
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterObject,
    ValidClan,
    ValidTrait,
)
from valentina.utils.helpers import fetch_random_name
from valentina.utils.options import (
    select_char_class,
    select_country,
    select_player_character,
    select_storyteller_character,
    select_trait,
    select_trait_two,
    select_vampire_clan,
)
from valentina.utils.perform_roll import perform_roll
from valentina.utils.storyteller import storyteller_character_traits
from valentina.views import ConfirmCancelButtons, present_embed
from valentina.views.character_sheet import sheet_embed, show_sheet

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

    @storyteller.command(name="create_character", description="Create a new npc character")
    async def create_story_char(
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

    @storyteller.command(name="list_characters", description="List all characters")
    async def list_characters(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all storyteller characters."""
        characters = self.bot.char_svc.fetch_all_storyteller_characters(ctx=ctx)

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

    @storyteller.command(name="sheet", description="View a character sheet")
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
        await show_sheet(ctx, character=character, claimed_by=None)

    @storyteller.command(name="delete_character", description="Delete a character")
    async def delete_character(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to delete",
            autocomplete=select_storyteller_character,
            required=True,
        ),
    ) -> None:
        """Delete a storyteller character."""
        view = ConfirmCancelButtons(ctx.author)
        embed = await sheet_embed(
            ctx, character, title=f"Confirm deletion of {character.full_name}"
        )
        msg = await ctx.respond(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if not view.confirmed:
            await msg.edit_original_response(  # type: ignore [union-attr]
                embed=discord.Embed(
                    title=f"{character.full_name} not deleted",
                    color=EmbedColor.WARNING.value,
                ),
            )
            return

        character.delete_instance(delete_nullable=True, recursive=True)
        self.bot.char_svc.purge_cache(ctx)
        await msg.edit_original_response(  # type: ignore [union-attr]
            embed=discord.Embed(
                title=f"{character.full_name} deleted",
                color=EmbedColor.SUCCESS.value,
            ),
        )
        await self.bot.guild_svc.send_to_audit_log(
            ctx,
            discord.Embed(
                title="Storyteller character deleted",
                description=f"Deleted {character.full_name}",
                color=EmbedColor.SUCCESS.value,
            ),
        )

    @storyteller.command(name="roll_traits", description="Roll traits for a character")
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
            ValidTrait,
            description="First trait to roll",
            required=True,
            autocomplete=select_trait,
        ),
        trait_two: Option(
            ValidTrait,
            description="Second trait to roll",
            required=True,
            autocomplete=select_trait_two,
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

    @storyteller.command(name="grant_xp", description="Grant xp to a player character")
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

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title=f"Grant `{xp}` xp to `{character.name}`?",
            ephemeral=hidden,
            level="info",
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="XP Grant Cancelled",
                    description="",
                    color=EmbedColor.WARNING.value,
                )
            )
            return

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "experience": new_xp,
                "experience_total": new_xp_total,
            },
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, f"`{character.name}` granted `{xp}` xp")
        await msg.edit_original_response(
            embed=discord.Embed(
                title=f"`{character.name}` granted `{xp}` xp",
                description="",
                color=EmbedColor.SUCCESS.value,
            )
        )

    @storyteller.command(name="grant_cp", description="Grant a cool point to a player character")
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

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title=f"Grant `{cp}` cool {p.plural_noun('member', cp)} (`{xp_amount}` xp) to `{character.name}`?",
            inline_fields=True,
            ephemeral=hidden,
            level="info",
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Cool point grant cancelled",
                    description="",
                    color=EmbedColor.WARNING.value,
                )
            )
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

        await self.bot.guild_svc.send_to_audit_log(
            ctx,
            f"Grant `{cp}` cool {p.plural_noun('point', cp)} (`{xp_amount}` xp) to `{character.name}`",
        )
        await msg.edit_original_response(
            embed=discord.Embed(
                title=f"Granted `{cp}` cool {p.plural_noun('point', cp)} (`{xp_amount}` xp) to `{character.name}`",
                description="",
                color=EmbedColor.SUCCESS.value,
            )
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(StoryTeller(bot))
