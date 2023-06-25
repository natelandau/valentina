# mypy: disable-error-code="valid-type"

"""A cog for handling XP and leveling up."""
import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, char_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.utils.errors import NoClaimError
from valentina.utils.helpers import (
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
    normalize_to_db_row,
)
from valentina.views import ConfirmCancelButtons, present_embed


class Xp(commands.Cog, name="XP"):
    """Add or spend experience points."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    xp = discord.SlashCommandGroup("xp", "Add or spend xp")

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

    @xp.command(name="spend", description="Spend experience points to upgrade a trait")
    @logger.catch
    async def spend_xp(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            str,
            description="Trait to raise with xp",
            required=True,
            autocomplete=__trait_autocomplete,
        ),
    ) -> None:
        """Spend experience points."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed",
                description="You must claim a character before you can spend experience.\nTo claim a character, use `/character claim`.",
                level="error",
                ephemeral=True,
            )
            return

        old_value = character.__getattribute__(normalize_to_db_row(trait))

        try:
            if old_value > 0:
                multiplier = get_trait_multiplier(trait)
                upgrade_cost = (old_value + 1) * multiplier

            if old_value == 0:
                upgrade_cost = get_trait_new_value(trait)

            if old_value >= get_max_trait_value(trait):
                await present_embed(
                    ctx,
                    title=f"Error: {trait} at max value",
                    description=f"**{trait}** is already at max value of {old_value}.",
                    level="error",
                )
                return
            view = ConfirmCancelButtons(ctx.author)
            await present_embed(
                ctx,
                title=f"Upgrade {trait}",
                description=f"Upgrading **{trait}** by **1** dot will cost **{upgrade_cost} XP**",
                fields=[
                    (f"Current {trait} value", old_value),
                    (f"New {trait} value", old_value + 1),
                    ("Current XP", character.experience),
                    ("XP Cost", upgrade_cost),
                    ("Remaining XP", character.experience - upgrade_cost),
                ],
                inline_fields=False,
                ephemeral=True,
                level="info",
                view=view,
            )
            await view.wait()
            if view.confirmed:
                new_value = old_value + 1
                new_experience = character.experience - upgrade_cost
                char_svc.update_char(
                    ctx.guild.id,
                    character.id,
                    **{normalize_to_db_row(trait): new_value, "experience": new_experience},
                )
                logger.info(f"XP: {character.name} {trait} upgraded by {ctx.author.name}")
                await present_embed(
                    ctx=ctx,
                    title=f"{character.name} {trait} upgraded",
                    description=f"**{trait}** upgraded to **{new_value}**.",
                    level="success",
                    fields=[("Remaining XP", new_experience)],
                    footer=f"Updated by {ctx.author.name}",
                )
        except ValueError:
            await present_embed(
                ctx,
                title="Error: No XP cost",
                description=f"**{trait}** does not have an XP cost in `XPMultiplier`",
                level="error",
                ephemeral=True,
            )
            return

    @xp.command(name="add", description="Add experience to a character")
    @logger.catch
    async def add_xp(
        self,
        ctx: discord.ApplicationContext,
        exp: Option(int, description="The amount of experience to add", required=True),
    ) -> None:
        """Add experience to a character."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed",
                description="You must claim a character before you can add experience.\nTo claim a character, use `/character claim`.",
                level="error",
            )
            return

        exp = int(exp)
        new_exp = character.experience + exp
        new_total = character.experience_total + exp

        char_svc.update_char(
            ctx.guild.id,
            character.id,
            experience=new_exp,
            experience_total=new_total,
        )
        logger.info(f"EXP: {character.name} exp updated by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title=f"{character.name} experience update.",
            description=f"**{exp}** experience points added.",
            fields=[("Current xp", new_exp)],
            level="success",
            footer=f"{new_total} all time xp",
        )

    @xp.command(name="cp", description="Add cool points to a character")
    @logger.catch
    async def add_cool_points(
        self,
        ctx: discord.ApplicationContext,
        cp: Option(int, description="The number of cool points to add", required=True),
    ) -> None:
        """Add cool points to a character."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed",
                description="You must claim a character before you can add cool points.\nTo claim a character, use `/character claim`.",
                level="error",
            )
            return

        cp = int(cp)
        new_cp = character.cool_points + cp
        new_total = character.cool_points_total + cp

        char_svc.update_char(
            ctx.guild.id,
            character.id,
            cool_points=new_cp,
            cool_points_total=new_total,
        )
        logger.info(f"CP: {character.name} cool points updated by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title=f"{character.name} cool points updated",
            description=f"**{cp}** cool points added.",
            fields=[("Current Cool Points", new_cp)],
            level="success",
            footer=f"{new_total} all time cool points",
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Xp(bot))
