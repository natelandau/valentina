"""A wizard that walks the user through the character creation process."""
from types import SimpleNamespace
from typing import Any

import discord
from discord.ui import Button
from loguru import logger

from valentina.models.constants import FLAT_TRAITS
from valentina.models.database import Character, CharacterClass, Guild
from valentina.views.rating_view import RatingView


class Wizard:
    """A character creation wizard."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        parameters: SimpleNamespace,
    ) -> None:
        self.ctx = ctx
        self.parameters = parameters
        self.using_dms = True
        self.msg = None  # We will be editing this message instead of sending new ones
        self.assigned_traits: dict[str, int] = {}
        self.core_traits = FLAT_TRAITS.copy()
        logger.info(
            f"CHARGEN: Started by {ctx.user.name}#{ctx.user.discriminator} on {ctx.guild.name}"
        )
        self.view = RatingView(self._assign_next_trait, self._timeout)

    async def __finalize_character(self) -> None:
        """Add the character to the database and inform the user they are done."""
        db_guild = Guild.get(Guild.guild_id == self.ctx.guild.id)
        db_char_class = CharacterClass.get(CharacterClass.name == self.parameters.char_class)

        Character.create(
            first_name=self.parameters.first_name,
            last_name=self.parameters.last_name,
            char_class=db_char_class.id,
            guild=db_guild.id,
            **self.assigned_traits,
        )
        logger.info(
            f"DATABASE: Add {self.parameters.char_class} character {self.parameters.first_name}."
        )
        logger.info(
            f"CHARGEN: Completed by {self.ctx.user.name}#{self.ctx.user.discriminator} on {self.ctx.guild.name}"
        )

        self.view.stop()
        await self.__finalize_embed()

    async def __finalize_embed(self) -> None:
        """Display finalizing message in an embed."""
        embed = discord.Embed(
            title="Success!",
            description=f"{self.parameters.char_class} **{self.parameters.first_name}** has been created in ***{self.ctx.guild.name}***!",
            colour=discord.Color.blue(),
        )
        embed.set_author(
            name=f"Valentina on {self.ctx.guild.name}", icon_url=self.ctx.guild.icon or ""
        )
        embed.add_field(name="Make a mistake?", value="Use `/traits` to fix.")
        embed.add_field(
            name="Want to add Discipline ratings or custom traits?",
            value=(
                f"Use `/traits add` on {self.ctx.guild.name}. "
                "Add specialties with `/specialties add`."
            ),
            inline=False,
        )

        embed.set_footer(text="See /help for further details.")

        button: discord.ui.Button = Button(
            label=f"Back to {self.ctx.guild.name}", url=self.ctx.guild.jump_url
        )

        await self.edit_message(embed=embed, view=discord.ui.View(button))

    def __query_embed(self, message: str = None) -> discord.Embed:
        """Present the query in an embed."""
        description = "This wizard will guide you through the character creation process.\n\n"
        if message is not None:
            description = message

        embed = discord.Embed(
            title=f"Select the rating for: {self.core_traits[0]}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.parameters.first_name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        return embed

    async def __query_trait(
        self, *, interaction: discord.Interaction = None, message: str = None
    ) -> None:
        """Query for the next trait."""
        embed = self.__query_embed(message)

        if self.msg is None:
            # First time we're sending the message. Try DMs first and fallback
            # to ephemeral messages if that fails. We prefer DMs so the user
            # always has a copy of the documentation link.
            if self.using_dms:
                try:
                    self.msg = await self.ctx.author.send(embed=embed, view=self.view)
                    # If successful, we post this message in the originating channel
                    await self.ctx.respond(
                        "Please check your DMs! I hope you have your character sheet ready.",
                        ephemeral=True,
                    )
                except discord.errors.Forbidden:
                    self.using_dms = False

            if not self.using_dms:
                self.msg = await self.ctx.respond(embed=embed, view=self.view, ephemeral=True)  # type: ignore [assignment]

        else:
            # Message is being edited
            await interaction.response.edit_message(embed=embed, view=self.view)  # type: ignore [unreachable]

    async def _assign_next_trait(self, rating: int, interaction: discord.Interaction) -> None:
        """Assign the next trait.

        Assign the next trait in the list and display the next trait or finish
        creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
            interaction (discord.Interaction): The interaction that triggered
        """
        trait = self.core_traits.pop(0)
        self.assigned_traits[trait.lower()] = rating

        if not self.core_traits:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            await self.__query_trait(message=f"{trait} set to {rating}.", interaction=interaction)

    async def _timeout(self) -> None:
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your character generation on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
        logger.info("CHARACTER CREATE: Timed out")

    async def begin_chargen(self) -> None:
        """Start the chargen wizard."""
        if self.core_traits:
            await self.__query_trait()
        else:
            await self.__finalize_character()

    @property
    def edit_message(self) -> Any:
        """Get the proper edit method for editing our message outside of an interaction."""
        if self.msg:
            return self.msg.edit  # type: ignore [unreachable]
        return self.ctx.respond
