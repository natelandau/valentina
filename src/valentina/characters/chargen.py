"""A RNG character generator for Valentina."""
from typing import cast

import discord
import inflect
from discord.ext import pages
from discord.ui import Button
from numpy.random import default_rng

from valentina.constants import (
    CharClassType,
    CharConcept,
    EmbedColor,
    Emoji,
    VampireClanType,
)
from valentina.models.bot import Valentina
from valentina.models.db_tables import (
    Campaign,
    Character,
    GuildUser,
)
from valentina.views import ChangeNameModal, sheet_embed

from .reallocate_dots import ReallocateDots

p = inflect.engine()
p.defnoun("Ability", "Abilities")
_rng = default_rng()


class CharacterPickerButtons(discord.ui.View):
    """Buttons to select a character from the CharGenWizard paginator."""

    def __init__(self, ctx: discord.ApplicationContext, characters: list[Character]):
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

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Reroll (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="reroll",
        row=2,
    )
    async def reroll_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # TODO: Delete the characters
        self.reroll = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.CANCEL.value} Cancel (XP will be lost)",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel",
        row=2,
    )
    async def cancel_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Disable all buttons and stop the view."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        self.cancelled = True
        self.stop()

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a character."""
        await interaction.response.defer()
        # Disable the interaction and grab the setting name
        for child in self.children:
            if (
                isinstance(child, Button)
                and interaction.data.get("custom_id", None) == child.custom_id
            ):
                child.label = f"{Emoji.YES.value} {child.label}"

            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        # Return the selected character based on the custom_id of the button that was pressed
        self.selected = self.characters[int(interaction.data.get("custom_id", None))]  # type: ignore [call-overload]
        self.pick_character = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class BeginCancelCharGenButtons(discord.ui.View):
    """Buttons to begin or to cancel the character generation wizard."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.roll: bool = None

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
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

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
        await interaction.response.defer()
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.roll = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id


class UpdateCharacterButtons(discord.ui.View):
    """Buttons to update a character."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        character: Character,
        author: discord.User | discord.Member | None = None,
    ):
        super().__init__()
        self.ctx = ctx
        self.character = character
        self.author = author
        self.updated: bool = False
        self.done: bool = False

        # TODO: Allow the user to change select their special ability
        # TODO: Allow the user update their trait values

    @discord.ui.button(
        label=f"{Emoji.PENCIL.value} Rename",
        style=discord.ButtonStyle.primary,
        custom_id="rename",
        row=2,
    )
    async def rename_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Callback for the rename button."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        modal = ChangeNameModal(ctx=self.ctx, character=self.character, title="Rename Character")
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
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Callback for the reallocate button."""
        await interaction.response.defer()
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        shift_dots = ReallocateDots(self.ctx, self.character)
        updated, character = await shift_dots.execute()
        if updated:
            self.character = character

        self.updated = True
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Done",
        style=discord.ButtonStyle.success,
        custom_id="done",
        row=3,
    )
    async def done_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the done button."""
        await interaction.response.defer()
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        self.done = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.ctx.author.id


class CharGenWizard:
    """A step-by-step character generation wizard."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        campaign: Campaign,
        user: GuildUser,
        hidden: bool = True,
    ) -> None:
        self.ctx = ctx
        self.interaction = ctx.interaction
        self.bot = cast(Valentina, ctx.bot)
        self.user = user
        self.campaign = campaign
        self.hidden = hidden
        self.paginator: pages.Paginator = None  # Container for the paginator

    async def _create_rng_character(self) -> Character:
        """Generate a character."""
        return await self.bot.char_svc.rng_creator(self.ctx, chargen_character=True)

    async def _create_char_sheet_embed(
        self,
        character: Character,
        title: str | None = None,
        prefix: str | None = None,
    ) -> discord.Embed:
        """Create an embed for a character."""
        concept_info = CharConcept[character.data["concept_db"]].value

        special_abilities = (
            [
                f"{i}. **{ability['name']}:** {ability['description']}\n"
                for i, ability in enumerate(concept_info["abilities"], start=1)
            ]
            if character.char_class.name in [CharClassType.MORTAL.name, CharClassType.HUNTER.name]
            else [
                f"{character.char_class.name.title()}s do not receive special abilities from their concept"
            ]
        )

        suffix = f"""
**{character.full_name} is a {concept_info['name']}**
{concept_info['description']}

**Special {p.plural_noun('Ability', len(concept_info["abilities"]))}:**
{''.join(special_abilities)}
"""

        return await sheet_embed(
            self.ctx,
            character,
            title=title if title else f"{character.full_name}",
            desc_prefix=prefix,
            desc_suffix=suffix,
        )

    async def _cancel_chargen(self, spent_xp: bool = False, not_enough_xp: bool = False) -> None:
        """Cancel the character generation wizard."""
        if not_enough_xp:
            description = "Not enough XP to reroll"
        if spent_xp:
            description = "No character was created but you lost 10 XP for wasting my time."
        else:
            description = "No character was created."

        embed = discord.Embed(
            title=f"{Emoji.CANCEL.value} Cancelled",
            description=description,
            color=EmbedColor.WARNING.value,
        )
        embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
        await self.paginator.cancel(page=embed, include_custom=True)

    async def start(self, restart: bool = False) -> None:
        """Start the character generation wizard."""
        # Build the embeds
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
                    f"- **`{c.value['range'][1] - c.value['range'][0]}%` {c.value['name']}** {c.value['description']}"
                    for c in CharClassType
                    if c.value["range"] is not None
                ]
            ),
            color=EmbedColor.INFO.value,
        )
        embed3 = discord.Embed(
            title="Concepts",
            description="\n".join(
                [
                    f"- **{c.value['name']}** {c.value['description']}"
                    for c in CharConcept
                    if c.value["range"] is not None
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
            await self._cancel_chargen()
            return

        self.user.spend_experience(self.campaign.id, 10)
        await self.select_character()

    async def select_character(self) -> None:
        """Start the character generation wizard."""
        # Generate 3 characters
        characters = [await self._create_rng_character() for i in range(3)]

        # Add the pages to the paginator
        description = f"## Created {len(characters)} {p.plural_noun('character', len(characters))} for you to choose from\n"
        character_list = [
            f"{i}. **{c.full_name}:**  A {CharConcept[c.data['concept_db']].value['name']} {VampireClanType[c.clan.name].value['name'] if c.clan else ''} {CharClassType[c.char_class.name].value['name']}"
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
        pages.extend([await self._create_char_sheet_embed(character) for character in characters])

        # present the character selection paginator
        # TODO: Fix interaction which works but says it doesn't
        view = CharacterPickerButtons(self.ctx, characters)
        await self.paginator.update(
            pages=pages,  # type: ignore [arg-type]
            custom_view=view,
            timeout=600,
        )
        await view.wait()

        if view.cancelled:
            await self._cancel_chargen(spent_xp=True)
            return
        if view.reroll:
            (
                campaign_xp,
                _,
                _,
                _,
                _,
            ) = self.user.fetch_experience(self.campaign.id)
            if campaign_xp < 10:  # noqa: PLR2004
                await self._cancel_chargen(not_enough_xp=True)
                return
            await self.start(restart=True)

        if view.pick_character:
            selected_character = view.selected

            for c in characters:
                if c.id != selected_character.id:
                    # Delete the characters the user did not select
                    c.delete_instance(delete_nullable=True, recursive=True)
                if c.id == selected_character.id:
                    # Add the selected character to the player's character list
                    data: dict[str, str | int | bool] = {
                        "chargen_character": False,
                        "player_character": True,
                    }
                    await self.bot.char_svc.update_or_add(self.ctx, character=c, data=data)

            # Post-process the character
            await self.character_review(selected_character)

    async def character_review(self, character: Character) -> Character:
        """Update the selected character."""
        title = f"{Emoji.YES.value} Created {character.full_name}\n"
        embed = await self._create_char_sheet_embed(character, title=title)

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
            await self.character_review(view.character)

        if view.done:
            # TODO: Spend 21 freebie points
            embed = discord.Embed(
                title=f"{Emoji.SUCCESS.value} Created {character.name}",
                description="Thanks for using my character generation wizard.",
                color=EmbedColor.SUCCESS.value,
            )
            embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
            await self.paginator.cancel(page=embed, include_custom=True)

            return character

        return None
