"""A RNG character generator for Valentina."""

from typing import cast

import discord
import inflect
from beanie import DeleteRules
from discord.ext import pages
from discord.ui import Button
from loguru import logger
from numpy.random import default_rng

from valentina.constants import (
    STARTING_FREEBIE_POINTS,
    CharacterConcept,
    CharClass,
    EmbedColor,
    Emoji,
    RNGCharLevel,
    VampireClan,
)
from valentina.controllers import ChannelManager, RNGCharGen, delete_character
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.views import ChangeNameModal, sheet_embed
from valentina.models import Campaign, Character, User

from .reallocate_dots import DotsReallocationWizard
from .spend_experience import SpendFreebiePoints

p = inflect.engine()
p.defnoun("Ability", "Abilities")
_rng = default_rng()


class CharacterPickerButtons(discord.ui.View):  # pragma: no cover
    """Manage buttons for selecting a character in the CharGenWizard paginator.

    Args:
        ctx (ValentinaContext): The context of the Discord application.
        characters (list[Character]): List of characters to choose from.

    Attributes:
        pick_character (bool): Whether a character was picked.
        selected (Character): The selected character.
        reroll (bool): Whether to reroll characters.
        cancelled (bool): Whether the selection was cancelled.
    """

    def __init__(self, ctx: ValentinaContext, characters: list[Character]):
        super().__init__(timeout=3000)
        self.ctx = ctx
        self.characters = characters
        self.pick_character: bool = False
        self.selected: Character = None
        self.reroll: bool = False
        self.cancelled: bool = False

        # Create a button for each character
        for i, character in enumerate(characters):
            button: Button = Button(
                label=f"{i + 1}. {character.full_name}",
                custom_id=f"{i}",
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.button_callback  # type: ignore [method-assign]
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a character."""
        await interaction.response.defer()
        self._disable_all()
        index = int(interaction.data.get("custom_id", None))  # type: ignore
        self.selected = self.characters[index]
        self.pick_character = True
        self.stop()

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Reroll (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="reroll",
        row=2,
    )
    async def reroll_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.reroll = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
        row=2,
    )
    async def cancel_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        self._disable_all()
        self.cancelled = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class BeginCancelCharGenButtons(discord.ui.View):  # pragma: no cover
    """Manage buttons for initiating or canceling the character generation process.

    This view provides buttons for users to either start rolling characters or cancel the process.

    Args:
        author (discord.User | discord.Member | None): The author of the interaction.
            If provided, only this user can interact with the buttons.

    Attributes:
        roll (bool | None): Indicates whether to roll for characters.
            Set to True if the roll button is clicked, False if cancelled, None otherwise.
    """

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.roll: bool = None

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Roll Characters (10xp)",
        style=discord.ButtonStyle.success,
        custom_id="roll",
        row=2,
    )
    async def roll_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the roll button."""
        await interaction.response.defer()
        button.label += f" {Emoji.YES.value}"
        self._disable_all()

        self.roll = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
        row=2,
    )
    async def cancel_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the cancel button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        self._disable_all()
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.roll = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id


class UpdateCharacterButtons(discord.ui.View):  # pragma: no cover
    """Manage buttons for updating a character's attributes.

    This view provides interactive buttons for various character update operations,
    such as renaming the character or reallocating attribute dots.

    Args:
        ctx (ValentinaContext): The context of the Discord application.
        character (Character): The character to update.
        author (discord.User | discord.Member | None): The author of the interaction.

    Attributes:
        updated (bool): Indicates whether the character has been updated.
        done (bool): Indicates whether the update process is complete.
    """

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
        author: discord.User | discord.Member | None = None,
    ):
        super().__init__()
        self.ctx = ctx
        self.character = character
        self.author = author
        self.updated: bool = False
        self.done: bool = False

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.PENCIL.value} Rename",
        style=discord.ButtonStyle.primary,
        custom_id="rename",
        row=2,
    )
    async def rename_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the rename button."""
        self._disable_all()

        modal = ChangeNameModal(character=self.character, title="Rename Character")
        await interaction.response.send_modal(modal)
        await modal.wait()

        self.character = modal.character
        self.updated = True
        self.stop()

    @discord.ui.button(
        label="💪 Reallocate Dots",
        style=discord.ButtonStyle.primary,
        custom_id="reallocate",
        row=2,
    )
    async def reallocate_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the reallocate button."""
        await interaction.response.defer()
        self._disable_all()

        dot_wizard = DotsReallocationWizard(self.ctx, self.character)
        updated, character = await dot_wizard.start_wizard()
        if updated:
            self.character = character

        self.updated = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Done Reallocating Dots",
        style=discord.ButtonStyle.success,
        custom_id="done",
        row=3,
    )
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the done button."""
        await interaction.response.defer()
        button.disabled = True
        self._disable_all()
        self.done = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class FreebiePointsButtons(discord.ui.View):  # pragma: no cover
    """Manage buttons for spending freebie points."""

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
    ):
        super().__init__()
        self.ctx = ctx
        self.character = character
        self.updated: bool = False
        self.done: bool = False

        button: Button = Button(
            label=f"💪 Spend {self.character.freebie_points} Freebie Points",
            style=discord.ButtonStyle.primary,
            custom_id="freebie_points",
            row=2,
        )
        button.callback = self.freebie_callback  # type: ignore [method-assign]
        self.add_item(button)

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    async def freebie_callback(self, interaction: discord.Interaction) -> None:
        """Callback for the reallocate button."""
        await interaction.response.defer()
        self._disable_all()

        freebie_wizard = SpendFreebiePoints(self.ctx, self.character)
        updated, character = await freebie_wizard.start_wizard()
        if updated:
            self.character = character

        self.updated = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Done Spending Freebie Points",
        style=discord.ButtonStyle.success,
        custom_id="done",
        row=3,
    )
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the done button."""
        await interaction.response.defer()
        button.disabled = True
        self._disable_all()
        self.done = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class CharGenWizard:  # pragma: no cover
    """Guide the user through a step-by-step character generation process.

    This class manages the interactive process of creating a new character,
    handling user inputs and generating character attributes.
    """

    # TODO: Allow the user to select their special ability when a choice is available
    # TODO: Improve mages, changelings, werewolves, and ghouls

    def __init__(
        self,
        ctx: ValentinaContext,
        campaign: Campaign,
        user: User,
        experience_level: RNGCharLevel = None,
        hidden: bool = False,
    ) -> None:
        self.ctx = ctx
        self.interaction = ctx.interaction
        self.bot = cast("Valentina", ctx.bot)

        self.user = user
        self.campaign = campaign
        self.experience_level = experience_level
        self.hidden = hidden

        self.paginator: pages.Paginator = None  # Initialize paginator to None
        self.engine = RNGCharGen(
            guild_id=self.ctx.guild.id, user=user, experience_level=self.experience_level
        )

    @staticmethod
    def _special_ability_char_sheet_text(character: Character) -> str:
        """Generate the special abilities text for the character sheet.

        Generate and format the special abilities text for a character's sheet,
        specifically for mortal characters. For non-mortal characters, return None.

        Args:
            character (Character): The character object for which to generate
                the special abilities text.

        Returns:
            str | None: A formatted string containing the character's concept,
                description, and special abilities if the character is a mortal.
                Returns None for non-mortal characters.
        """
        # Extract concept information for mortals
        if character.char_class.name == CharClass.MORTAL.name:
            concept_info = CharacterConcept[character.concept_name].value

            # Generate special abilities list
            special_abilities = [
                f"{i}. **{ability['name']}:** {ability['description']}\n"
                for i, ability in enumerate(concept_info.abilities, start=1)
            ]

            return f"""
    **{character.name} is a {concept_info.name}**
    {concept_info.description}

    **Special {p.plural_noun("Ability", len(concept_info.abilities))}: **
    {"".join(special_abilities)}
    """
        # Return None unless the character is a mortal
        return None

    async def _generate_character_sheet_embed(
        self,
        character: Character,
        title: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> discord.Embed:
        """Create an embed for the character sheet.

        Generate and return a Discord embed representing a character sheet.

        Args:
            character (Character): The character for which to create the embed.
            title (str | None): The title of the embed. If None, uses the character's name.
            prefix (str | None): Additional text to prepend to the embed description.
            suffix (str | None): Additional text to append to the embed description.

        Returns:
            discord.Embed: The created embed containing the character sheet information.
        """
        # Create the embed
        return await sheet_embed(
            self.ctx,
            character,
            title=title or f"{character.name}",
            desc_prefix=prefix,
            desc_suffix=suffix,
            show_footer=False,
        )

    async def _cancel_character_generation(
        self, msg: str | None = None, characters: list[Character] = []
    ) -> None:
        """Cancel the character generation process and clean up resources.

        This method handles the cancellation of character generation, deleting any partially
        created characters and displaying a cancellation message to the user.

        Args:
            msg (str | None): Custom message to display upon cancellation. If None, a default
                message is used.
            characters (list[Character]): List of Character objects to be deleted. These are
                typically partially created characters that need to be removed from the database.
        """
        if not msg:
            msg = "No character was created."

        for character in characters:
            await delete_character(character)

        embed = discord.Embed(
            title=f"{Emoji.CANCEL.value} Cancelled",
            description=msg,
            color=EmbedColor.WARNING.value,
        )
        embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
        await self.paginator.cancel(page=embed, include_custom=True)

    async def start(self, restart: bool = False) -> None:
        """Initiate the character generation wizard.

        Start or restart the character generation process, presenting the user with
        instructional embeds and options to begin or cancel character creation.

        Args:
            restart (bool): If True, restart the wizard with existing paginator.
                If False, create a new paginator. Defaults to False.
        """
        logger.debug("Starting the character generation wizard.")

        # Build the instructional embeds
        embed1 = discord.Embed(
            title="Create a new character",
            description="""\
For the cost of 10xp, I will generate three characters for you to choose between.  You select the one you want to keep.
### How this works
By rolling percentile dice we select a class and a concept.  The concept guides how default dots are added to your character.

Once you select a character you can re-allocate dots and change the name, but you cannot change the concept, class, or clan.

*View the possible classes and concepts by scrolling through the pages below*
""",
            color=EmbedColor.INFO.value,
        )
        embed2 = discord.Embed(
            title="Classes",
            description="\n".join(
                [
                    f"- **`{c.value.percentile_range[1] - c.value.percentile_range[0]}%` {c.value.name}** {c.value.description}"
                    for c in CharClass.playable_classes()
                ]
            ),
            color=EmbedColor.INFO.value,
        )
        embed3 = discord.Embed(
            title="Concepts",
            description="\n".join(
                [
                    f"- **{c.value.name}** {c.value.description}"
                    for c in CharacterConcept
                    if c.value.percentile_range is not None
                ]
            ),
            color=EmbedColor.INFO.value,
        )

        # Create and display the paginator
        view = BeginCancelCharGenButtons(self.ctx.author)
        if restart:
            await self.paginator.update(pages=[embed1, embed2, embed3], custom_view=view)  # type: ignore [arg-type]
        else:
            self.paginator = pages.Paginator(
                pages=[embed1, embed2, embed3],  # type: ignore [arg-type]
                custom_view=view,
                author_check=True,
                timeout=600,
            )
            self.paginator.remove_button("first")
            self.paginator.remove_button("last")
            await self.paginator.respond(self.ctx.interaction, ephemeral=self.hidden)

        await view.wait()

        if not view.roll:
            await self._cancel_character_generation()
            return

        # Spend 10 XP
        await self.user.spend_campaign_xp(self.campaign, 10)

        # Move on reviewing three options
        await self.present_character_choices()

    async def present_character_choices(self) -> None:
        """Guide the user through the character selection process.

        Generate three random characters and present them to the user for selection.
        Display character details using a paginator, allowing the user to review
        and choose a character, reroll for new options, or cancel the process.

        This method handles the core logic of character generation and selection,
        including trait assignment and presentation of character options.

        Returns:
            None
        """
        logger.debug("Starting the character selection process")

        # Generate 3 characters
        characters = [
            await self.engine.generate_full_character(chargen_character=True) for _ in range(3)
        ]

        # Add the pages to the paginator
        description = f"## Created {len(characters)} {p.plural_noun('character', len(characters))} for you to choose from\n"
        character_list = [
            f"{i}. **{c.name}:**  A {CharacterConcept[c.concept_name].value.name} {VampireClan[c.clan_name].value.name if c.clan_name else ''} {CharClass[c.char_class.name].value.name}"
            for i, c in enumerate(characters)
        ]
        description += "\n".join(character_list)
        description += """
### Next Steps
1. **Review the details for each character** by scrolling through their sheets
2. **Select the character you want to play** by selecting a button below; or
3. **Reroll all characters** by selecting the reroll button for a cost of `10 XP`

**Important:**
Once you select a character you can re-allocate dots and change the name, but you cannot change the concept, class, or clan.
"""

        pages: list[discord.Embed] = [
            discord.Embed(
                title="Character Generations", description=description, color=EmbedColor.INFO.value
            )
        ]
        pages.extend(
            [
                await self._generate_character_sheet_embed(
                    character, suffix=character.concept_description()
                )
                for character in characters
            ]
        )

        # present the character selection paginator
        view = CharacterPickerButtons(self.ctx, characters)
        await self.paginator.update(
            pages=pages,  # type: ignore [arg-type]
            custom_view=view,
            timeout=600,
        )
        await view.wait()

        if view.cancelled:
            await self._cancel_character_generation(
                msg="No character was created but you lost 10 XP for wasting my time.",
                characters=characters,
            )
            return

        if view.reroll:
            campaign_xp, _, _ = self.user.fetch_campaign_xp(self.campaign)

            # Delete the previously created characters
            logger.debug("Rerolling characters and deleting old ones.")
            for character in characters:
                await delete_character(character)

            # Check if the user has enough XP to reroll
            if campaign_xp < 10:  # noqa: PLR2004
                await self._cancel_character_generation(
                    msg="Not enough XP to reroll.", characters=characters
                )
                return

            # Restart the character generation process
            await self.start(restart=True)

        if view.pick_character:
            selected_character = view.selected

            for c in characters:
                if c.id != selected_character.id:
                    # Delete the characters the user did not select
                    await c.delete(link_rule=DeleteRules.DELETE_LINKS)

                if c.id == selected_character.id:
                    # Add the player into the database
                    c.freebie_points = STARTING_FREEBIE_POINTS
                    c.type_player = True
                    c.type_chargen = False
                    await c.save()

                    self.user.characters.append(c)
                    await self.user.save()

                    selected_character = c

            # Post-process the character
            await self.finalize_character_selection(selected_character)

    async def finalize_character_selection(self, character: Character) -> None:
        """Review and finalize the selected character.

        Present the user with an updated character sheet and allow them to finalize
        the character or make additional changes.

        Args:
            character (Character): The selected character to review and finalize.
        """
        logger.debug(f"CHARGENL Update the character: {character.full_name}")

        # Create the character sheet embed
        title = f"{Emoji.YES.value} Created {character.full_name}\n"
        embed = await self._generate_character_sheet_embed(
            character, title=title, suffix=self._special_ability_char_sheet_text(character)
        )

        # Update the paginator
        view = UpdateCharacterButtons(self.ctx, character=character, author=self.ctx.author)
        await self.paginator.update(
            pages=[embed],  # type: ignore [arg-type]
            custom_view=view,
            show_disabled=False,
            show_indicator=False,
            timeout=600,
        )

        await view.wait()
        if view.updated:
            # Restart the view and show the changes
            await self.finalize_character_selection(view.character)

        if view.done:
            await self.spend_freebie_points(character)

        if self.campaign:
            character.campaign = str(self.campaign.id)
            await character.save()

            channel_manager = ChannelManager(guild=self.ctx.guild)
            await channel_manager.confirm_character_channel(
                character=character, campaign=self.campaign
            )
            await channel_manager.sort_campaign_channels(self.campaign)

    async def spend_freebie_points(self, character: Character) -> Character:
        """Spend freebie points on a character.

        Present the user with an interface to allocate freebie points to various
        character traits. This method handles the process of spending freebie points,
        updating the character sheet, and finalizing the character creation.

        Args:
            character (Character): The character to spend freebie points on.

        Returns:
            Character: The updated character after spending freebie points.
        """
        logger.debug(f"Spending freebie points for {character.name}")

        # Create the character sheet embed
        title = f"Spend freebie points on {character.name}\n"
        suffix = f"Use the buttons below to chose where you want to spend your `{character.freebie_points}` remaining freebie points.\n"
        embed = await self._generate_character_sheet_embed(character, title=title, suffix=suffix)

        # Update the paginator
        view = FreebiePointsButtons(self.ctx, character=character)
        await self.paginator.update(
            pages=[embed],  # type: ignore [arg-type]
            custom_view=view,
            show_disabled=False,
            show_indicator=False,
            timeout=600,
        )

        await view.wait()
        if view.updated:
            # Restart the view and show the changes
            await self.spend_freebie_points(view.character)

        if view.done:
            # End the wizard
            embed = discord.Embed(
                title=f"{Emoji.SUCCESS.value} Created {character.name}",
                description="Thanks for using my character generation wizard.",
                color=EmbedColor.SUCCESS.value,
            )
            embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
            await self.paginator.cancel(page=embed, include_custom=True)

        return character
