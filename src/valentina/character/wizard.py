"""A wizard that walks the user through the character creation process."""
import asyncio
import uuid
from typing import Any

import discord
from discord.ui import Button
from loguru import logger

from valentina.models.constants import MAX_BUTTONS_PER_ROW, EmbedColor
from valentina.models.db_tables import Trait
from valentina.utils.helpers import get_max_trait_value


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


class CharGenWizard:
    """Character creation wizard."""

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
