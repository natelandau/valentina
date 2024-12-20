"""A wizard that walks the user through the character creation process."""

import asyncio
import uuid
from collections.abc import Callable

import discord
from beanie import WriteRules
from discord.ui import Button
from loguru import logger

from valentina.constants import MAX_BUTTONS_PER_ROW, EmbedColor
from valentina.controllers import ChannelManager, CharacterSheetBuilder, TraitForCreation
from valentina.discord.bot import ValentinaContext
from valentina.models import Campaign, Character, CharacterTrait, User


class RatingView(discord.ui.View):  # pragma: no cover
    """A View that lets the user select a rating."""

    def __init__(  # type: ignore [no-untyped-def]
        self,
        trait_to_enter: TraitForCreation,
        callback,
        failback,
    ) -> None:
        """Initialize the view."""
        super().__init__(timeout=300)
        self.callback = callback
        self.failback = failback

        # Trait Info
        self.trait_name = trait_to_enter.name
        self.trait_category = trait_to_enter.category
        self.max_value = trait_to_enter.max_value

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
        self.last_interaction = interaction

        await self.callback(rating, interaction)


class AddFromSheetWizard:  # pragma: no cover
    """A character generation wizard for entering pre-existing characters.

    This wizard guides the user through the process of setting values for each trait
    of a character that has already been created on a physical character sheet.
    It provides an interactive interface to input trait values systematically,
    ensuring all necessary information is captured for the digital representation
    of the character.
    """

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

    def __grab_trait_names(self) -> list[TraitForCreation]:
        """Get the character's traits."""
        sheet_builder = CharacterSheetBuilder(character=self.character)
        return sheet_builder.fetch_all_class_traits_unorganized()

    async def begin_chargen(self) -> None:
        """Start the chargen wizard."""
        await self.__send_messages()

    async def wait_until_done(self) -> Character:
        """Wait until the wizard is done."""
        while self.trait_list:
            await asyncio.sleep(1)  # Wait a bit then check again

        return self.character

    async def __view_callback(self, rating: int, interaction: discord.Interaction) -> None:
        """Assign the next trait.

        Assign a value to the previously rated trait and display the next trait or finish creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
            max_value (int): The maximum value for the rating.
            interaction (discord.Interaction): The interaction that triggered
        """
        # Create a CharacterTrait from the first trait in the list, and remove it from the list
        completed_trait = self.trait_list.pop(0)

        # Append to dict to be turned into Character Traits later
        self.completed_traits.append(
            {
                "name": completed_trait.name,
                "category_name": completed_trait.category.name,
                "value": rating,
                "max_value": completed_trait.max_value,
            }
        )

        if not self.trait_list:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            # Rate the next trait
            await self.__send_messages(
                message=f"`{completed_trait.name} set to {rating}`",
                interaction=interaction,
            )

    async def __finalize_character(
        self,
    ) -> None:
        """Finalize character creation and notify the user.

        Add the character to the database, create associated traits, link to a campaign
        if applicable, update the user's character list, create a character channel
        if in a campaign, and send a confirmation message to the user.

        This method handles the final steps of character creation after all traits
        have been input by the user.

        Raises:
            discord.errors.HTTPException: If there's an error creating the character's channel.
            beanie.exceptions.DocumentSaveError: If there's an error saving the character or user data.
        """
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
            channel_manager = ChannelManager(guild=self.ctx.guild)
            await channel_manager.confirm_character_channel(
                character=self.character, campaign=self.campaign
            )
            await channel_manager.sort_campaign_channels(self.campaign)

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
        """Send messages to query trait information during character creation.

        This method handles the process of sending messages to the user to gather
        trait information for character creation. It prepares and sends an embed
        with the current trait being queried, and sets up the view for user interaction.

        Args:
            interaction (discord.Interaction | None): The interaction object if this
                method is called in response to a user interaction. Defaults to None.
            message (str | None): An optional message to include in the embed description.
                Defaults to None.

        Raises:
            discord.errors.HTTPException: If there's an error sending the message.
            discord.errors.Forbidden: If the bot doesn't have permission to send messages.
        """
        trait_to_enter = self.trait_list[0]

        description = "This wizard will guide you through the character creation process.\n\n"

        if message is not None:
            description = message

        # Build the embed
        embed = discord.Embed(
            title=f"Select the rating for: {trait_to_enter.name}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.character.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        # Build the view with the first trait in the list. (Note, it is removed from the list in the callback)

        self.view = RatingView(trait_to_enter, self.__view_callback, self.__timeout)

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
            await interaction.response.edit_message(embed=embed, view=self.view)

    async def __timeout(self) -> None:
        """Inform the user that their character generation session has timed out due to inactivity.

        This method is called when the user fails to respond within the allotted time during
        the character creation process. It sends a message to the user, cancels the character
        generation, and logs the timeout event.

        Raises:
            discord.errors.HTTPException: If there's an error sending the message.
            discord.errors.Forbidden: If the bot doesn't have permission to send messages.
        """
        errmsg = f"Due to inactivity, your character generation on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
        logger.info("CHARGEN: Timed out")

    @property
    def edit_message(self) -> Callable:
        """Get the appropriate edit method for modifying messages outside of an interaction.

        Returns:
            Callable: The edit method to use. If self.msg exists, returns self.msg.edit,
                      otherwise returns self.ctx.respond.

        This property determines the correct method to use for editing messages
        in different contexts, allowing for flexible message manipulation
        throughout the character creation process.
        """
        if self.msg:
            return self.msg.edit
        return self.ctx.respond
