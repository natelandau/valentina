# mypy: disable-error-code="valid-type"
"""Commands for the storyteller."""
import discord
from discord.commands import Option
from discord.ext import commands
from peewee import fn

from valentina.models.bot import Valentina
from valentina.models.constants import DEFAULT_DIFFICULTY, DiceType
from valentina.models.db_tables import VampireClan
from valentina.models.dicerolls import DiceRoll
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterObject,
    ValidClan,
)
from valentina.utils.helpers import fetch_random_name
from valentina.utils.options import (
    select_char_class,
    select_country,
    select_storyteller_character,
    select_trait,
    select_trait_two,
    select_vampire_clan,
)
from valentina.utils.storyteller import storyteller_character_traits
from valentina.views import ConfirmCancelButtons, ReRollButton, present_embed
from valentina.views.character_sheet import sheet_embed, show_sheet
from valentina.views.roll_display import RollDisplay


class StoryTeller(commands.Cog):
    """Commands for the storyteller."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def _perform_roll(
        self,
        ctx: discord.ApplicationContext,
        pool: int,
        difficulty: int,
        dice_size: int,
        comment: str | None = None,
        trait_one_name: str | None = None,
        trait_one_value: int | None = None,
        trait_two_name: str | None = None,
        trait_two_value: int | None = None,
    ) -> None:
        """Perform a dice roll and display the result.

        Args:
            ctx (discord.ApplicationContext): The context of the command.
            pool (int): The number of dice to roll.
            difficulty (int): The difficulty of the roll.
            dice_size (int): The size of the dice.
            comment (str, optional): A comment to display with the roll. Defaults to None.
            trait_one_name (str, optional): The name of the first trait. Defaults to None.
            trait_one_value (int, optional): The value of the first trait. Defaults to None.
            trait_two_name (str, optional): The name of the second trait. Defaults to None.
            trait_two_value (int, optional): The value of the second trait. Defaults to None.
        """
        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=dice_size)

        while True:
            view = ReRollButton(ctx.author)
            embed = await RollDisplay(
                ctx,
                roll,
                comment,
                trait_one_name,
                trait_one_value,
                trait_two_name,
                trait_two_value,
            ).get_embed()
            await ctx.respond(embed=embed, view=view)
            await view.wait()
            if view.confirmed:
                roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=dice_size)
            else:
                break

    storyteller = discord.SlashCommandGroup(
        "storyteller",
        "Commands for the storyteller",
        checks=[commands.has_any_role("Storyteller", "Admin").predicate],  # type: ignore [attr-defined]
    )

    @storyteller.command(name="new_character", description="Create a new character")
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
        """Test command."""
        first_name, last_name = await fetch_random_name(gender=gender, country=name_type)

        if char_class.name.lower() == "vampire" and not vampire_clan:
            vampire_clan = VampireClan.select().order_by(fn.Random()).limit(1)[0]

        character = self.bot.char_svc.create_character(
            ctx,
            first_name=first_name,
            last_name=last_name,
            nickname=char_class.name,
            char_class=char_class,
            clan=vampire_clan,
            storyteller_character=True,
        )

        fetched_traits = self.bot.trait_svc.fetch_all_class_traits(char_class.name)
        trait_values = storyteller_character_traits(
            fetched_traits,
            level=level,
            specialty=specialty,
            clan=vampire_clan.name if vampire_clan else None,
        )

        self.bot.char_svc.update_traits_by_id(ctx, character, trait_values)

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
                    color=discord.Color.red(),
                ),
            )
            return

        await msg.edit_original_response(  # type: ignore [union-attr]
            embed=discord.Embed(
                title=f"{character.full_name} saved",
                color=discord.Color.green(),
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
                    color=discord.Color.red(),
                ),
            )
            return

        character.delete_instance(delete_nullable=True, recursive=True)
        self.bot.char_svc.purge_cache(ctx)
        await msg.edit_original_response(  # type: ignore [union-attr]
            embed=discord.Embed(
                title=f"{character.full_name} deleted",
                color=discord.Color.green(),
            ),
        )
        await self.bot.guild_svc.send_to_audit_log(
            ctx,
            discord.Embed(
                title="Storyteller character deleted",
                description=f"Deleted {character.full_name}",
                color=discord.Color.green(),
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
            str,
            description="First trait to roll",
            required=True,
            autocomplete=select_trait,
        ),
        trait_two: Option(
            str,
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
    ) -> None:
        """Roll traits for a storyteller character."""
        trait_one = self.bot.trait_svc.fetch_trait_from_name(trait_one)
        trait_two = self.bot.trait_svc.fetch_trait_from_name(trait_two)

        trait_one_value = character.trait_value(trait_one)
        trait_two_value = character.trait_value(trait_two)

        pool = trait_one_value + trait_two_value

        await self._perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one_name=trait_one.name,
            trait_one_value=trait_one_value,
            trait_two_name=trait_two.name,
            trait_two_value=trait_two_value,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(StoryTeller(bot))
