"""A wizard that walks the user through the character creation process."""

import asyncio
import uuid
from typing import Any

import discord
from beanie import WriteRules
from discord.ui import Button
from loguru import logger

from valentina.constants import MAX_BUTTONS_PER_ROW, EmbedColor, TraitCategory
from valentina.models import Campaign, Character, CharacterTrait, User
from valentina.models.bot import ValentinaContext
from valentina.utils.helpers import get_max_trait_value


class RatingView(discord.ui.View):
    """A View that lets the user select a rating."""

    def __init__(  # type: ignore [no-untyped-def]
        self,
        trait_name: str,
        trait_category: TraitCategory,
        callback,
        failback,
    ) -> None:
        """Initialize the view."""
        super().__init__(timeout=300)
        self.callback = callback
        self.failback = failback

        # Trait Info
        self.trait_name = trait_name
        self.trait_category = trait_category
        self.max_value = get_max_trait_value(self.trait_name, self.trait_category.name)

        # Interaction Info
        self.ratings: dict[str, int] = {}
        self.response: int = None
        self.last_interaction = None

        # Add buttons for each rating
        for rating in range(1, self.max_value + 1):
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
        max_value = self.max_value
        self.last_interaction = interaction

        await self.callback(rating, max_value, interaction)


class AddFromSheetWizard:
    """A character generation wizard that walks the user through setting a value for each trait. This is used for entering a character that has already been created from a physical character sheet."""

    def __init__(
        self,
        ctx: ValentinaContext,
        character: Character,
        user: User,
        campaign: Campaign | None = None,
    ) -> None:
        self.ctx = ctx
        self.character = character
        self.user = user
        self.msg: discord.Message = None
        self.trait_list = self.__grab_trait_names()
        self.completed_traits: list[dict] = []
        self.campaign = campaign

    def __grab_trait_names(self) -> list[tuple[str, TraitCategory]]:
        """Get the character's traits."""
        traits = []
        for t in sorted(TraitCategory, key=lambda x: x.value.order):
            traits.extend(
                [(x, t) for x in t.value.COMMON]
                + [(x, t) for x in getattr(t.value, self.character.char_class_name)]
            )

        return traits

    async def begin_chargen(self) -> None:
        """Start the chargen wizard."""
        await self.__send_messages()

    async def wait_until_done(self) -> Character:
        """Wait until the wizard is done."""
        while self.trait_list:
            await asyncio.sleep(1)  # Wait a bit then check again

        return self.character

    async def __view_callback(
        self, rating: int, max_value: int, interaction: discord.Interaction
    ) -> None:
        """Assign the next trait.

        Assign a value to the previously rated trait and display the next trait or finish creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
            max_value (int): The maximum value for the rating.
            interaction (discord.Interaction): The interaction that triggered
        """
        # Create a CharacterTrait from the first trait in the list, and remove it from the list
        trait_name, trait_category = self.trait_list.pop(0)

        # Append to dict to be turned into Character Traits later
        self.completed_traits.append(
            {
                "name": trait_name,
                "category_name": trait_category.name,
                "value": rating,
                "max_value": max_value,
            }
        )

        if not self.trait_list:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            # Rate the next trait
            await self.__send_messages(
                message=f"`{trait_name} set to {rating}`",
                interaction=interaction,
            )

    async def __finalize_character(
        self,
    ) -> None:
        """Add the character to the database and inform the user they are done."""
        # Add the character to the database
        await self.character.insert()

        # Create a list of Character Traits
        traits_to_add = [
            CharacterTrait(
                name=x["name"],
                value=x["value"],
                category_name=x["category_name"],
                character=str(self.character.id),
                max_value=x["max_value"],
            )
            for x in self.completed_traits
        ]

        # Associate the character with a campaign
        if self.campaign:
            self.character.campaign = str(self.campaign.id)

        # Write the traits to the database
        self.character.traits = traits_to_add  # type: ignore [assignment]
        await self.character.save(link_rule=WriteRules.WRITE)

        # Add the character to the user's list of characters
        self.user.characters.append(self.character)
        await self.user.save()

        # Create channel
        if self.campaign:
            await self.character.confirm_channel(self.ctx, self.campaign)
            await self.campaign.sort_channels(self.ctx)

        # Respond to the user
        embed = discord.Embed(
            title="Success!",
            description=f"{self.character.name} has been created",
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
        trait_name, trait_category = self.trait_list[0]

        description = "This wizard will guide you through the character creation process.\n\n"

        if message is not None:
            description = message

        # Build the embed
        embed = discord.Embed(
            title=f"Select the rating for: {trait_name}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.character.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        # Build the view with the first trait in the list. (Note, it is removed from the list in the callback)

        self.view = RatingView(trait_name, trait_category, self.__view_callback, self.__timeout)

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
            await interaction.response.edit_message(embed=embed, view=self.view)  # type: ignore [union-attr]

    async def __timeout(self) -> None:
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your character generation on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
        logger.info("CHARGEN: Timed out")

    @property
    def edit_message(self) -> Any:
        """Get the proper edit method for editing our message outside of an interaction."""
        if self.msg:
            return self.msg.edit
        return self.ctx.respond
