"""Create a character."""

import re

import discord
from loguru import logger
from peewee import fn

from valentina.character.wizard import Wizard
from valentina.models.database import Character, Guild
from valentina.views.embeds import present_embed


class CharGenModal(discord.ui.Modal):
    """A modal creating characters."""

    def __init__(self, char_class: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.char_class = char_class
        self.humanity: str = None
        self.willpower: str = None
        self.blood_pool: str = None
        self.arete: str = None
        self.quintessence: str = None
        self.gnosis: str = None
        self.rage: str = None
        self.conviction: str = None

        self.add_item(
            discord.ui.InputText(
                label="Willpower",
                style=discord.InputTextStyle.short,
                required=True,
                placeholder="Enter a number",
                max_length=2,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Humanity",
                style=discord.InputTextStyle.short,
                required=True,
                placeholder="Enter a number",
                max_length=2,
            )
        )
        match char_class.lower():
            case "mage":
                self.add_item(
                    discord.ui.InputText(
                        label="Arete",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    discord.ui.InputText(
                        label="Quintessence",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "werewolf":
                self.add_item(
                    discord.ui.InputText(
                        label="Rage",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    discord.ui.InputText(
                        label="Gnosis",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "vampire":
                self.add_item(
                    discord.ui.InputText(
                        label="Blood Pool",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "hunter":
                self.add_item(
                    discord.ui.InputText(
                        label="Conviction",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
        ############################################################################3

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Modal Results")
        self.willpower = self.children[0].value
        self.humanity = self.children[1].value
        embed.add_field(name="Willpower", value=self.children[0].value)
        embed.add_field(name="Humanity", value=self.children[1].value)
        if self.char_class.lower() == "mage":
            embed.add_field(name="Arete", value=self.children[2].value)
            embed.add_field(name="Quintessence", value=self.children[3].value)
            self.arete = self.children[2].value
            self.quintessence = self.children[3].value
        elif self.char_class.lower() == "werewolf":
            embed.add_field(name="Rage", value=self.children[2].value)
            embed.add_field(name="Gnosis", value=self.children[3].value)
            self.rage = self.children[2].value
            self.gnosis = self.children[3].value
        elif self.char_class.lower() == "vampire":
            embed.add_field(name="Blood Pool", value=self.children[2].value)
            self.blood_pool = self.children[2].value
        elif self.char_class.lower() == "hunter":
            embed.add_field(name="Conviction", value=self.children[2].value)
            self.conviction = self.children[2].value

        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        self.stop()


async def create_character(
    ctx: discord.ApplicationContext,
    quick_char: bool,
    char_class: str,
    first_name: str,
    last_name: str,
    nickname: str = None,
) -> None:
    """Create a character.

    Args:
        char_class (str): The character's class
        ctx (discord.ApplicationContext): The context of the command
        first_name (str): The character's first name
        last_name (str, optional): The character's last name. Defaults to None.
        nickname (str, optional): The character's nickname. Defaults to None.
        quick_char (bool, optional): Create a character with only essential traits?.
        willpower (int): The character's willpower
        humanity (int): The character's humanity
    """
    try:
        # Remove extraenous spaces from the name
        first_name = re.sub(r"\s+", " ", first_name).strip()
        last_name = re.sub(r"\s+", " ", last_name).strip() if last_name else None

        # Error handling
        for n in first_name, last_name, nickname:
            if n:
                __validate_name(n)
        __unique_name(ctx, first_name, last_name, nickname)

        # Gather additional information from modal
        modal = CharGenModal(title="Additional character information", char_class=char_class)
        await ctx.send_modal(modal, ephemeral=True)
        await modal.wait()
        willpower = int(modal.willpower) if modal.willpower else 0
        humanity = int(modal.humanity) if modal.humanity else 0
        arete = int(modal.arete) if modal.arete else 0
        quintessence = int(modal.quintessence) if modal.quintessence else 0
        rage = int(modal.rage) if modal.rage else 0
        gnosis = int(modal.gnosis) if modal.gnosis else 0
        blood_pool = int(modal.blood_pool) if modal.blood_pool else 0
        conviction = int(modal.conviction) if modal.conviction else 0

        # Create the character
        character_wizard = Wizard(
            ctx,
            quick_char=quick_char,
            char_class=char_class,
            first_name=first_name,
            last_name=last_name,
            nickname=nickname,
            willpower=willpower,
            humanity=humanity,
            arete=arete,
            quintessence=quintessence,
            rage=rage,
            gnosis=gnosis,
            blood_pool=blood_pool,
            conviction=conviction,
        )
        await character_wizard.begin_chargen()

    except ValueError as e:
        logger.debug(f"CHARGEN: User input did not validate: {e}")
        await present_embed(
            ctx, title="Error in Character Generation", description=str(e), level="ERROR"
        )


def __validate_name(name: str) -> None:
    """Validates names (first, last, and nicknames).

    Args:
        name (str): The name to validate
    """
    errors = []
    max_len = 30

    if (name_len := len(name)) > max_len:
        errors.append(f"`{name}` is too long by {name_len - max_len} characters.")

    if not re.match(r"^[a-zA-Z0-9 _-]+$", name):
        errors.append("`{name}` may only contain letters, spaces, hyphens, and underscores.")


def __unique_name(
    ctx: discord.ApplicationContext, first_name: str, last_name: str | None, nickname: str | None
) -> None:
    """Ensure that the name of the character is unique in the database."""
    errors = []
    first_name = first_name.lower() if first_name else None
    last_name = last_name.lower() if last_name else None
    nickname = nickname.lower() if nickname else None

    if last_name is not None:
        search = (
            fn.LOWER(Character.first_name)
            == first_name & fn.LOWER(Character.last_name)
            == last_name
        )
    else:
        search = fn.LOWER(Character.first_name) == first_name

    query = Character.select().where(search).join(Guild).where(Guild.id == ctx.guild.id)
    if len(query) > 0:
        if last_name is not None:
            errors.append(f"A character with the name `{first_name} {last_name}` already exists.")
        else:
            errors.append(f"A character with the name `{first_name}` already exists.")

    if nickname is not None:
        query = (
            Character.select()
            .where(fn.LOWER(Character.nickname) == nickname)
            .join(Guild)
            .where(Guild.id == ctx.guild.id)
        )
        if len(query) > 0:
            errors.append(f"A character with the nickname `{nickname}` already exists.")

    if errors:
        err = "\n".join(errors)
        raise ValueError(err)
