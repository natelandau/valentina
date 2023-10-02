"""A wizard that walks the user through the character creation process."""
import asyncio
import uuid
from typing import Any, cast

import discord
import inflect
from discord.ui import Button
from loguru import logger

from valentina.constants import (
    CONCEPT_INFORMATION,
    MAX_BUTTONS_PER_ROW,
    CharGenClass,
    CharGenConcept,
    CharGenHumans,
    DiceType,
    EmbedColor,
    Emoji,
)
from valentina.models.bot import Valentina
from valentina.models.db_tables import Campaign, GuildUser, Trait
from valentina.models.dicerolls import DiceRoll
from valentina.utils.helpers import get_max_trait_value

p = inflect.engine()
p.defnoun("Ability", "Abilities")

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


class RollButton(discord.ui.View):
    """Add a 'roll' button to a view.  Used as the first step in the character generation wizard."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None

    @discord.ui.button(
        label=f"{Emoji.DICE.value} Roll", style=discord.ButtonStyle.success, custom_id="roll"
    )
    async def roll_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label += f" {Emoji.DICE.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        if self.author is None:
            return True
        return interaction.user.id == self.author.id


class ConfirmRerollButtons(discord.ui.View):
    """Add a submit and cancel button to a view."""

    def __init__(self, author: discord.User | discord.Member | None = None):
        super().__init__()
        self.author = author
        self.confirmed: bool = None
        self.rerolled: bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.confirmed = True
        self.rerolled = False
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.DICE.value} ReRoll",
        style=discord.ButtonStyle.secondary,
        custom_id="reroll",
    )
    async def reroll_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label += f" {Emoji.YES.value}"
        button.disabled = True
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True
        await interaction.response.edit_message(view=None)  # view=None remove all buttons
        self.rerolled = True
        self.confirmed = False
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
        msg: discord.Interaction,
        hidden: bool = True,
    ) -> None:
        self.ctx = ctx
        self.bot = cast(Valentina, ctx.bot)
        self.user = user
        self.campaign = campaign
        self.hidden = hidden
        self.msg = msg
        self.char_class: CharGenClass = None
        self.char_sub_class: CharGenHumans = None
        self.char_concept: CharGenConcept = None

    async def _step_1_class(self) -> None:
        """Randomly select the base class for the character."""
        roll = DiceRoll(self.ctx, pool=1, dice_size=DiceType.D100.value).roll[0]
        view = RollButton(self.ctx.author)
        class_descriptions = "\n".join(
            [f"{c.value[0]}-{c.value[1]}: {c.name.title().replace('_', ' ')}" for c in CharGenClass]
        )

        await self.msg.edit_original_response(
            embed=discord.Embed(
                title="Character Generation",
                description=f"""\
The first step is to roll a 100 sided die to determine your class.

### Options
```yaml
{class_descriptions}
```
""",
                color=EmbedColor.INFO.value,
            ).set_footer(text="Step 1/5"),
            view=view,
        )

        await view.wait()
        self.char_class = CharGenClass.get_member_by_value(roll)

        # Handle unimplemented classes
        if self.char_class != CharGenClass.HUMAN:
            await self.msg.edit_original_response(
                embed=discord.Embed(
                    title="Character Generation",
                    description=f"You rolled a `{roll}`\n This makes you a {self.char_class.name.title().replace('_', ' ')}\n\nUnfortunately, `{self.char_class.name.title().replace('_', ' ')}` is not implemented.\n\nRoll your sheet manually and use `/character add` to add it to the database.",
                    color=EmbedColor.INFO.value,
                ).set_footer(text="Step 2/2"),
            )
            return

        await self._step_2_subclass(roll)

    async def _step_2_subclass(self, previous_roll: int) -> None:
        """Randomly select the secondary class for the character."""
        roll = DiceRoll(self.ctx, pool=1, dice_size=DiceType.D100.value).roll[0]
        view = RollButton(self.ctx.author)
        subclass_descriptions = "\n".join(
            [
                f"{c.value[0]}-{c.value[1]}: {c.name.title().replace('_', ' ')}"
                for c in CharGenHumans
            ]
        )

        await self.msg.edit_original_response(
            embed=discord.Embed(
                title="Character Generation",
                description=f"""\
You rolled a `{previous_roll}`. Your class is: `{self.char_class.name.title().replace('_', ' ')}`

The next step is to roll a 100 sided die to determine your {self.char_class.name.title().replace('_', ' ')} sub-class.

### Options
```yaml
{subclass_descriptions}
```
""",
                color=EmbedColor.INFO.value,
            ).set_footer(text="Step 2/5"),
            view=view,
        )

        await view.wait()
        self.char_sub_class = CharGenHumans.get_member_by_value(roll)

        await self._step_3_concept(roll)

    async def _step_3_concept(self, previous_roll: int) -> None:
        """Randomly select the secondary class for the character."""
        roll = DiceRoll(self.ctx, pool=1, dice_size=DiceType.D100.value).roll[0]
        view = RollButton(self.ctx.author)
        concept_descriptions = "\n".join(
            [
                f"{c.value[0]}-{c.value[1]}: {c.name.title().replace('_', ' ')}"
                for c in CharGenConcept
            ]
        )

        await self.msg.edit_original_response(
            embed=discord.Embed(
                title="Character Generation",
                description=f"""\
You rolled a `{previous_roll}`. Your subclass is: `{self.char_sub_class.name.title().replace('_', ' ')}`

The next step is to roll a 100 sided die to determine your character's concept.

### Options
```yaml
{concept_descriptions}
```
""",
                color=EmbedColor.INFO.value,
            ).set_footer(text="Step 3/5"),
            view=view,
        )

        await view.wait()
        self.char_concept = CharGenConcept.get_member_by_value(roll)
        await self._step_4_class_review(previous_roll=roll)

    async def _step_4_class_review(self, previous_roll: int) -> None:
        """Finalize the character."""
        view = ConfirmRerollButtons(self.ctx.author)

        # Get the concept's abilities
        abilities = CONCEPT_INFORMATION[self.char_concept]["abilities"]
        num_abilities = CONCEPT_INFORMATION[self.char_concept]["num_abilities"]
        ability_list = "\n".join(
            [f"- **{special['name']}**: {special['description']}" for special in abilities]
        )
        ability_text = (
            f"Choose {p.number_to_words(num_abilities)} from this list:\n"  # type: ignore [arg-type]
            if num_abilities < len(abilities)
            else ""
        )

        # Get the user's current xp
        (
            campaign_xp,
            _,
            _,
            _,
            _,
        ) = self.user.fetch_experience(self.campaign.id)

        await self.msg.edit_original_response(
            embed=discord.Embed(
                title="Character Generation",
                description=f"""\
You rolled a `{previous_roll}`. Your concept is: `{self.char_concept.name.title().replace('_', ' ')}`.
## Review your character class
**You are a {self.char_class.name.title().replace('_', ' ')} {self.char_sub_class.name.title().replace('_', ' ')} {self.char_concept.name.title().replace('_', ' ')}**
_{CONCEPT_INFORMATION[self.char_concept]["description"]}_

**Examples:** {CONCEPT_INFORMATION[self.char_concept]["examples"]}
### Special {p.plural_noun('Ability', num_abilities)}
{ability_text}{ability_list}
## Next Steps:
Do you want to reroll for 10xp or confirm your character?
_(You have `{campaign_xp}`xp remaining.)_
""",
                color=EmbedColor.SUCCESS.value,
            ).set_footer(text="Step 4/5"),
            view=view,
        )
        await view.wait()
        if view.rerolled:
            self.user.spend_experience(self.campaign.id, 10)
            self.bot.user_svc.purge_cache(self.ctx)
            await self._step_1_class()
        # TODO: Go to step 4_1 if user must select a special ability
        elif view.confirmed:
            await self._step_5_create_character()

    async def _step_4_1_specialties(self) -> None:
        """Choose specialties."""

    async def _step_5_create_character(self) -> None:
        """Create the character."""
        await self.msg.edit_original_response(
            embed=discord.Embed(
                title="Character Generation",
                description=f"""\
Created a `{self.char_class.name.title().replace('_', ' ')}` `{self.char_sub_class.name.title().replace('_', ' ')}` `{self.char_concept.name.title().replace('_', ' ')}`

### Next Steps:
1. Roll your character sheet
2. Use `/character add` to add your character to the database
""",
                color=EmbedColor.SUCCESS.value,
            ).set_footer(text="Step 5/5"),
        )

    async def begin(self) -> None:
        """Start the character generation wizard."""
        await self._step_1_class()
