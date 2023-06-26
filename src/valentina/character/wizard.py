"""A wizard that walks the user through the character creation process."""

from typing import Any

import discord
from discord.ui import Button
from loguru import logger

from valentina import user_svc
from valentina.models.constants import (
    CLAN_DISCIPLINES,
    COMMON_TRAITS,
    MAGE_TRAITS,
    WEREWOLF_TRAITS,
)
from valentina.models.database import Character, CharacterClass, VampireClan
from valentina.views import RatingView


class Wizard:
    """A character creation wizard."""

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        quick_char: bool,
        properties: dict[str, Any],
    ) -> None:
        self.ctx = ctx
        self.quick_char = quick_char
        self.properties = properties

        self.using_dms = True
        self.msg = None  # We will be editing this message instead of sending new ones
        self.assigned_traits: dict[str, int] = {}
        self.traits_to_enter = self.__define_traits_to_enter()
        logger.debug(f"CHARGEN: Started by {ctx.user.name} on {ctx.guild.name}")
        self.view = RatingView(self._assign_next_trait, self._timeout)

    def __define_traits_to_enter(self) -> list[str]:
        """Builds the list of traits to enter during character generation."""
        traits_list: list[str] = []
        traits_list.extend(COMMON_TRAITS["Physical"])
        traits_list.extend(COMMON_TRAITS["Social"])
        traits_list.extend(COMMON_TRAITS["Mental"])

        if self.quick_char:
            traits_list.extend(["Alertness", "Dodge", "Firearms", "Melee"])
        else:
            traits_list.extend(COMMON_TRAITS["Talents"])
            traits_list.extend(COMMON_TRAITS["Skills"])
            traits_list.extend(COMMON_TRAITS["Knowledges"])

        traits_list.extend(COMMON_TRAITS["Virtues"])
        # Remove values set in modal view
        _universal = [x for x in COMMON_TRAITS["Universal"] if x not in ["Willpower", "Humanity"]]
        traits_list.extend(_universal)

        if self.properties["char_class"].lower() == "vampire":
            for clan, disciplines in CLAN_DISCIPLINES.items():
                if self.properties["vampire_clan"].lower() == clan.lower():
                    traits_list.extend(disciplines)

        if self.properties["char_class"].lower() == "mage":
            traits_list.extend(MAGE_TRAITS["Spheres"])

        if self.properties["char_class"].lower() == "werewolf":
            traits_list.extend(WEREWOLF_TRAITS["Renown"])

        return traits_list

    @logger.catch
    async def __finalize_character(self) -> None:
        """Add the character to the database and inform the user they are done."""
        # Find foreign keys
        db_char_class = CharacterClass.get(CharacterClass.name == self.properties["char_class"])
        self.properties["char_class"] = db_char_class.id

        if self.properties["vampire_clan"]:
            vampire_clan_id = VampireClan.get(VampireClan.name == self.properties["vampire_clan"])
            self.properties["clan_id"] = vampire_clan_id.id

        # Remove non-DB values
        self.properties.pop("vampire_clan")

        # Create the character
        character = Character.create(
            guild=self.ctx.guild.id,
            created_by=user_svc.fetch_user(self.ctx).id,
            **self.properties,
            **self.assigned_traits,
        )

        logger.info(f"DATABASE: Add {character.char_class.name} character {character.name}")
        logger.debug(f"CHARGEN: Completed by {self.ctx.user.name} on {self.ctx.guild.name}")

        self.view.stop()
        await self.__finalize_embed()

    async def __finalize_embed(self) -> None:
        """Display finalizing message in an embed."""
        embed = discord.Embed(
            title="Success!",
            description=f"{self.properties['char_class']} **{self.properties['first_name']}** has been created in ***{self.ctx.guild.name}***!",
            colour=discord.Color.blue(),
        )
        embed.set_author(
            name=f"Valentina on {self.ctx.guild.name}", icon_url=self.ctx.guild.icon or ""
        )
        embed.add_field(name="Make a mistake?", value="Use `/character update trait` to fix.")
        # TODO: Add notes on how to add custom traits

        embed.set_footer(text="See /help for further details.")

        button: discord.ui.Button = Button(
            label=f"Back to {self.ctx.guild.name}", url=self.ctx.guild.jump_url
        )

        await self.edit_message(embed=embed, view=discord.ui.View(button))

    def __query_embed(self, message: str | None = None) -> discord.Embed:
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
            name=f"Creating {self.properties['first_name']} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        return embed

    async def __query_trait(
        self, *, interaction: discord.Interaction | None = None, message: str | None = None
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
