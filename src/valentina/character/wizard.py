"""A wizard that walks the user through the character creation process."""

from typing import Any

import discord
from discord.ui import Button
from loguru import logger

from valentina import user_svc
from valentina.models.constants import (
    COMMON_TRAITS,
    MAGE_TRAITS,
    VAMPIRE_TRAITS,
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
        char_class: str,
        first_name: str,
        last_name: str,
        humanity: int,
        willpower: int,
        arete: int | None = None,
        quintessence: int | None = None,
        blood_pool: int | None = None,
        gnosis: int | None = None,
        rage: int | None = None,
        conviction: int | None = None,
        nickname: str | None = None,
        vampire_clan: str | None = None,
    ) -> None:
        self.ctx = ctx
        self.quick_char = quick_char
        self.char_class = char_class
        self.first_name = first_name.title()
        self.last_name = last_name.title()
        self.nickname = nickname
        self.humanity = humanity
        self.willpower = willpower
        self.arete = arete
        self.quintessence = quintessence
        self.blood_pool = blood_pool
        self.gnosis = gnosis
        self.rage = rage
        self.conviction = conviction
        self.vampire_clan = vampire_clan

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

        if not self.quick_char:
            if self.char_class == "Mage":
                traits_list.extend(MAGE_TRAITS["Spheres"])
            if self.char_class == "Vampire":
                traits_list.extend(VAMPIRE_TRAITS["Disciplines"])
            if self.char_class == "Werewolf":
                traits_list.extend(WEREWOLF_TRAITS["Renown"])

        return traits_list

    @logger.catch
    async def __finalize_character(self) -> None:
        """Add the character to the database and inform the user they are done."""
        db_char_class = CharacterClass.get(CharacterClass.name == self.char_class)

        vampire_clan_id = (
            VampireClan.get(VampireClan.name == self.vampire_clan) if self.vampire_clan else None
        )

        Character.create(
            first_name=self.first_name,
            last_name=self.last_name,
            nickname=self.nickname,
            char_class=db_char_class.id,
            humanity=self.humanity,
            willpower=self.willpower,
            arete=self.arete,
            quintessence=self.quintessence,
            blood_pool=self.blood_pool,
            gnosis=self.gnosis,
            rage=self.rage,
            conviction=self.conviction,
            guild=self.ctx.guild.id,
            created_by=user_svc.fetch_user(self.ctx).id,
            clan_id=vampire_clan_id.id,
            **self.assigned_traits,
        )
        display_name = f"{self.first_name.title()}"
        display_name += f" ({self.nickname.title()})" if self.nickname else ""
        display_name += f" {self.last_name.title() }" if self.last_name else ""
        logger.info(f"DATABASE: Add {self.char_class} character {display_name}")
        logger.debug(f"CHARGEN: Completed by {self.ctx.user.name} on {self.ctx.guild.name}")

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
            name=f"Creating {self.first_name} on {self.ctx.guild.name}",
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
