"""A wizard that walks the user through the character creation process."""
import asyncio
import uuid
from typing import Any, cast

import discord
import inflect
from discord.ext import pages
from discord.ui import Button
from loguru import logger
from numpy.random import default_rng

from valentina.constants import (
    MAX_BUTTONS_PER_ROW,
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
    Trait,
)
from valentina.utils.helpers import get_max_trait_value
from valentina.views import sheet_embed

p = inflect.engine()
p.defnoun("Ability", "Abilities")
_rng = default_rng()

## Add from sheet wizard


class RatingView(discord.ui.View):
    """A View that lets the user select a rating."""

    def __init__(  # type: ignore [no-untyped-def]
        self,
        trait: Trait,
        callback,
        failback,
    ) -> None:
        """Initialize the view."""
        super().__init__(timeout=300)
        self.callback = callback
        self.failback = failback

        self.trait_id = trait.id
        self.trait_name = trait.name
        self.trait_category = trait.category.name
        self.trait_max_value = get_max_trait_value(self.trait_name, self.trait_category)
        self.ratings: dict[str, int] = {}
        self.response: int = None
        self.last_interaction = None

        for rating in range(1, self.trait_max_value + 1):
            button_id = str(uuid.uuid4())
            self.ratings[button_id] = rating

            # Calculate the row number for the button
            row = 1 if rating <= MAX_BUTTONS_PER_ROW else 0

            button: Button = Button(
                label=str(rating), custom_id=button_id, style=discord.ButtonStyle.primary, row=row
            )
            button.callback = self.button_pressed  # type: ignore [method-assign]
            self.add_item(button)

        # Add the 0 button at the end, so it appears at the bottom
        zero_button_id = str(uuid.uuid4())
        self.ratings[zero_button_id] = 0
        zero_button: Button = Button(
            label="0", custom_id=zero_button_id, style=discord.ButtonStyle.secondary, row=2
        )
        zero_button.callback = self.button_pressed  # type: ignore [method-assign]
        self.add_item(zero_button)

    async def button_pressed(self, interaction) -> None:  # type: ignore [no-untyped-def]
        """Respond to the button."""
        button_id = interaction.data["custom_id"]
        rating = self.ratings.get(button_id, 0)
        self.last_interaction = interaction

        await self.callback(rating, interaction)


class AddFromSheetWizard:
    """A character generation wizard that walks the user through setting a value for each trait. This is used for entering a character that has already been created from a physical character sheet."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        all_traits: list[Trait],
        first_name: str | None = None,
        last_name: str | None = None,
        nickname: str | None = None,
    ) -> None:
        self.ctx = ctx
        self.msg = None
        self.all_traits = all_traits
        self.assigned_traits: list[tuple[Trait, int]] = []
        self.view: discord.ui.View = None

        self.name = first_name.title()
        self.name += f" ({nickname.title()})" if nickname else ""
        self.name += f" {last_name.title() }" if last_name else ""

    async def begin_chargen(self) -> None:
        """Start the chargen wizard."""
        await self.__send_messages()

    async def wait_until_done(self) -> list[tuple[Trait, int]]:
        """Wait until the wizard is done."""
        while self.all_traits:
            await asyncio.sleep(1)  # Wait a bit then check again

        return self.assigned_traits

    async def __view_callback(self, rating: int, interaction: discord.Interaction) -> None:
        """Assign the next trait.

        Assign a value to the previously rated trait and display the next trait or finish creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
            interaction (discord.Interaction): The interaction that triggered
        """
        # Remove the first trait from the list and assign it
        previously_rated_trait = self.all_traits.pop(0)
        self.assigned_traits.append((previously_rated_trait, rating))

        if not self.all_traits:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            await self.__send_messages(
                message=f"`{previously_rated_trait.name} set to {rating}`",
                interaction=interaction,
            )

    async def __finalize_character(
        self,
    ) -> None:
        """Add the character to the database and inform the user they are done."""
        embed = discord.Embed(
            title="Success!",
            description=f"{self.name} has been created",
            color=EmbedColor.INFO.value,
        )
        embed.set_author(
            name=f"Valentina on {self.ctx.guild.name}", icon_url=self.ctx.guild.icon or ""
        )
        embed.add_field(name="Make a mistake?", value="Use `/character update trait`", inline=False)
        embed.add_field(
            name="Need to add a trait?", value="Use `/character add trait`", inline=False
        )

        embed.set_footer(text="See /help for further details")

        button: discord.ui.Button = Button(
            label=f"Back to {self.ctx.guild.name}", url=self.ctx.guild.jump_url
        )

        self.view.stop()
        await self.edit_message(embed=embed, view=discord.ui.View(button))

    async def __send_messages(
        self, *, interaction: discord.Interaction | None = None, message: str | None = None
    ) -> None:
        """Query a trait."""
        trait_to_be_rated = self.all_traits[0]

        description = "This wizard will guide you through the character creation process.\n\n"

        if message is not None:
            description = message

        embed = discord.Embed(
            title=f"Select the rating for: {trait_to_be_rated.name}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        # Build the view with the first trait in the list. (Note, it is removed from the list in the callback)

        self.view = RatingView(trait_to_be_rated, self.__view_callback, self.__timeout)

        if self.msg is None:
            # Send DM with the character generation wizard as a DM. This is the first message.
            self.msg = await self.ctx.author.send(embed=embed, view=self.view)

            # Respond in-channel to check DM
            await self.ctx.respond(
                "Please check your DMs! I hope you have your character sheet ready.",
                ephemeral=True,
            )
        else:
            # Subsequent sends, edit the interaction of the DM
            await interaction.response.edit_message(embed=embed, view=self.view)  # type: ignore [unreachable]

    async def __timeout(self) -> None:
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your character generation on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
        logger.info("CHARGEN: Timed out")

    @property
    def edit_message(self) -> Any:
        """Get the proper edit method for editing our message outside of an interaction."""
        if self.msg:
            return self.msg.edit  # type: ignore [unreachable]
        return self.ctx.respond


## Character Generation Wizard


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
                style=discord.ButtonStyle.success,
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
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

        embed = interaction.message.embeds[0]
        embed.description = f"## {Emoji.CANCEL.value} Cancelled\nNo character was selected"
        embed.color = EmbedColor.WARNING.value  # type: ignore [method-assign, assignment]

        self.cancelled = True
        self.stop()

    async def button_callback(self, interaction: discord.Interaction) -> None:
        """Respond to selecting a character."""
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
    async def roll_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Callback for the roll button."""
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
        self.bot = cast(Valentina, ctx.bot)
        self.user = user
        self.campaign = campaign
        self.hidden = hidden
        self.paginator: pages.Paginator = None  # Container for the paginator

    async def _generate_character(self) -> Character:
        """Generate a character."""
        return await self.bot.char_svc.rng_creator(self.ctx, chargen_character=True)

    async def _character_embed_creator(self, character: Character) -> discord.Embed:
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
            title=f"{character.full_name}",
            desc_prefix=None,
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

    @staticmethod
    def _create_review_home_embed(characters: list[Character]) -> discord.Embed:
        """Create an embed for the home page of the character generation wizard."""
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

        return discord.Embed(
            title="Character Generations",
            description=description,
            color=EmbedColor.INFO.value,
        )

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
        characters = [await self._generate_character() for i in range(3)]

        # Add the pages to the paginator
        pages: list[discord.Embed] = [self._create_review_home_embed(characters)]
        pages.extend([await self._character_embed_creator(character) for character in characters])

        # present the character selection paginator
        # TODO: Fix interaction which works but says it doesn't
        view = CharacterPickerButtons(self.ctx, characters)
        await self.paginator.update(pages=pages, custom_view=view)  # type: ignore [arg-type]
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
            character = view.selected

            # Delete the other characters
            for c in characters:
                if c.id != character.id:
                    c.delete_instance(delete_nullable=True, recursive=True)
                if c.id == character.id:
                    # TODO: Remove this once we have a way to update the character
                    data: dict[str, str | int | bool] = {
                        "chargen_character": False,
                        "player_character": True,
                    }
                    await self.bot.char_svc.update_or_add(self.ctx, character=character, data=data)

            # TODO: Remove this once we have a way to update the character
            embed = discord.Embed(
                title=f"{Emoji.CANCEL.value} Cancelled",
                description=f"Created {character.full_name} for you to play",
                color=EmbedColor.WARNING.value,
            )
            embed.set_thumbnail(url=self.ctx.bot.user.display_avatar)
            await self.paginator.cancel(page=embed, include_custom=True)

        # TODO: Allow the user to change the name
        # TODO: Allow the user to change select their special ability
        # TODO: Allow the user update their trait values
