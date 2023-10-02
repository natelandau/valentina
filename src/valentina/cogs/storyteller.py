# mypy: disable-error-code="valid-type"
"""Commands for the storyteller."""
from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from loguru import logger
from peewee import fn

from valentina.constants import (
    DEFAULT_DIFFICULTY,
    VALID_IMAGE_EXTENSIONS,
    DiceType,
    EmbedColor,
)
from valentina.models.bot import Valentina
from valentina.models.db_tables import VampireClan
from valentina.utils.converters import (
    ValidCharacterClass,
    ValidCharacterName,
    ValidCharacterObject,
    ValidClan,
    ValidImageURL,
    ValidTraitCategory,
)
from valentina.utils.helpers import fetch_data_from_url, fetch_random_name
from valentina.utils.options import (
    select_any_player_character,
    select_char_class,
    select_country,
    select_player_character,
    select_storyteller_character,
    select_trait_category,
    select_trait_from_char_option,
    select_trait_from_char_option_two,
    select_vampire_clan,
)
from valentina.utils.perform_roll import perform_roll
from valentina.utils.storyteller import storyteller_character_traits
from valentina.views import (
    AddFromSheetWizard,
    ConfirmCancelButtons,
    S3ImageReview,
    confirm_action,
    present_embed,
    sheet_embed,
    show_sheet,
)

p = inflect.engine()


class StoryTeller(commands.Cog):
    """Commands for the storyteller."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

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

        wizard = AddFromSheetWizard(
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

        character = await self.bot.char_svc.update_or_add(
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
        name = await fetch_random_name(gender=gender, country=name_type)

        if char_class.name.lower() == "vampire" and not vampire_clan:
            vampire_clan = VampireClan.select().order_by(fn.Random()).limit(1)[0]

        data = {
            "first_name": name[0][0],
            "last_name": name[0][1],
            "nickname": char_class.name,
            "storyteller_character": True,
            "player_character": False,
        }

        character = await self.bot.char_svc.update_or_add(
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

        fields.extend(
            [
                (
                    character.full_name,
                    f"Class: `{character.char_class.name}`",
                )
                for character in sorted(characters, key=lambda x: x.name)
            ]
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
            autocomplete=select_trait_from_char_option,
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

    @character.command(name="image_add", description="Add an image to a storyteller character")
    async def add_image(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to add the image to",
            autocomplete=select_storyteller_character,
            required=True,
        ),
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
            character (ValidCharacterObject): The character to add the image to.
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

    @character.command(
        name="image_delete", description="Delete an image to a storyteller character"
    )
    async def delete_image(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to delete the image from",
            autocomplete=select_storyteller_character,
            required=True,
        ),
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
            character (ValidCharacterObject): The character to delete the image from.
            hidden (bool): Whether the interaction should only be visible to the user initiating it.

        Returns:
            None
        """
        # Generate the key prefix for the character's images
        key_prefix = self.bot.aws_svc.get_key_prefix(
            ctx, "character", character_id=character.id
        ).rstrip("/")

        # Initiate an S3ImageReview to allow the user to review and delete images
        await S3ImageReview(ctx, key_prefix, review_type="character", hidden=hidden).send(ctx)

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
        present_owner_name = character.owned_by.data.get("display_name", "Unknown")

        title = f"Transfer `{character.full_name}` from `{present_owner_name}` to `{new_owner.display_name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        await self.bot.user_svc.transfer_character_owner(ctx, character, new_owner)

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
            autocomplete=select_trait_from_char_option,
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
            autocomplete=select_trait_from_char_option,
        ),
        trait_two: Option(
            str,
            description="Second trait to roll",
            required=True,
            autocomplete=select_trait_from_char_option_two,
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
            from_macro=True,
            trait_one=trait_one,
            trait_one_value=trait_one_value,
            trait_two=trait_two,
            trait_two_value=trait_two_value,
            character=character,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(StoryTeller(bot))
