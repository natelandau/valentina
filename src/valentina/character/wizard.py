"""A wizard that walks the user through the character creation process."""

from typing import Any

import discord
from discord.ui import Button
from loguru import logger

from valentina.models.constants import (
    ATTRIBUTES,
    FLAT_TRAITS,
    HUNTER_TRAITS,
    MAGE_SPHERES,
    MAGE_TRAITS,
    UNIVERSAL_TRAITS,
    VAMPIRE_DISCIPLINES,
    VIRTUES,
    WEREWOLF_TRAITS,
)
from valentina.models.database import Character, CharacterClass, Guild
from valentina.views.rating_view import RatingView


class Wizard:
    """A character creation wizard."""

    def __init__(  # noqa: PLR0913
        self,
        ctx: discord.ApplicationContext,
        quick_char: bool,
        char_class: str,
        first_name: str,
        last_name: str = None,
        nickname: str = None,
    ) -> None:
        self.ctx = ctx
        self.quick_char = quick_char
        self.char_class = char_class
        self.first_name = first_name
        self.last_name = last_name
        self.nickname = nickname
        self.using_dms = True
        self.msg = None  # We will be editing this message instead of sending new ones
        self.assigned_traits: dict[str, int] = {}
        self.traits_to_enter = self.__define_traits_to_enter()
        logger.warning(f"DEBUG-A: {self.traits_to_enter}")
        logger.info(
            f"CHARGEN: Started by {ctx.user.name}#{ctx.user.discriminator} on {ctx.guild.name}"
        )
        self.view = RatingView(self._assign_next_trait, self._timeout)

    def __define_traits_to_enter(self) -> list[str]:
        """Builds the list of traits to enter during character generation."""
        traits_list: list[str] = []
        traits_list.extend(UNIVERSAL_TRAITS)
        traits_list.extend(ATTRIBUTES)
        traits_list.extend(VIRTUES)
        traits_list.extend(["Alertness", "Dodge", "Firearms", "Melee"])

        if self.char_class == "Mage":
            traits_list.extend(MAGE_TRAITS)
        if self.char_class == "Vampire":
            traits_list.extend(VAMPIRE_DISCIPLINES)
        if self.char_class == "Werewolf":
            traits_list.extend(WEREWOLF_TRAITS)
        if self.char_class == "Hunter":
            traits_list.extend(HUNTER_TRAITS)

        if not self.quick_char:
            traits_list.extend(FLAT_TRAITS.copy())

            if self.char_class == "Mage":
                traits_list.extend(MAGE_SPHERES)

        no_dupes = []
        [no_dupes.append(item) for item in traits_list if item not in no_dupes]  # type: ignore [func-returns-value]

        return no_dupes

    async def __finalize_character(self) -> None:
        """Add the character to the database and inform the user they are done."""
        db_guild = Guild.get(Guild.guild_id == self.ctx.guild.id)
        db_char_class = CharacterClass.get(CharacterClass.name == self.char_class)

        Character.create(
            first_name=self.first_name,
            last_name=self.last_name,
            char_class=db_char_class.id,
            guild=db_guild.id,
            **self.assigned_traits,
        )
        logger.info(f"DATABASE: Add {self.char_class} character {self.first_name}.")
        logger.info(
            f"CHARGEN: Completed by {self.ctx.user.name}#{self.ctx.user.discriminator} on {self.ctx.guild.name}"
        )

        self.view.stop()
        await self.__finalize_embed()

    async def __finalize_embed(self) -> None:
        """Display finalizing message in an embed."""
        embed = discord.Embed(
            title="Success!",
            description=f"{self.char_class} **{self.first_name}** has been created in ***{self.ctx.guild.name}***!",
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
            title=f"Select the rating for: {self.traits_to_enter[0]}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.first_name} on {self.ctx.guild.name}",
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
        logger.warning(f"debug: {self.traits_to_enter}")
        trait = self.traits_to_enter.pop(0)
        self.assigned_traits[trait.lower()] = rating

        if not self.traits_to_enter:
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
        if self.traits_to_enter:
            await self.__query_trait()
        else:
            await self.__finalize_character()

    @property
    def edit_message(self) -> Any:
        """Get the proper edit method for editing our message outside of an interaction."""
        if self.msg:
            return self.msg.edit  # type: ignore [unreachable]
        return self.ctx.respond
