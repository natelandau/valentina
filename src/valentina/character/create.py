"""Create a character."""
import discord

from valentina.character.views import CharGenModal, SelectClan
from valentina.character.wizard import Wizard


async def create_character(
    ctx: discord.ApplicationContext,
    quick_char: bool,
    char_class: str,
    first_name: str,
    last_name: str,
    nickname: str | None = None,
) -> None:
    """Create a character.

    Args:
        char_class (str): The character's class
        ctx (discord.ApplicationContext): The context of the command
        first_name (str): The character's first name
        last_name (str, optional): The character's last name. Defaults to None.
        nickname (str, optional): The character's nickname. Defaults to None.
        quick_char (bool, optional): Create a character with only essential traits?.
    """
    # Instantiate the property dictionary
    properties: dict[str, str | int] = {}

    properties["first_name"] = first_name
    properties["last_name"] = last_name if last_name else None
    properties["nickname"] = nickname if nickname else None
    properties["char_class"] = char_class

    # Gather universal trait information from the CharGenModal. This modal is used b/c these traits have a value that can be higher than 5 which is the maximum number of buttons presented in the wizard
    modal = CharGenModal(title="Additional character information", char_class=char_class)
    await ctx.send_modal(modal)
    await modal.wait()
    properties["humanity"] = int(modal.humanity) if modal.humanity else 0
    properties["willpower"] = int(modal.willpower) if modal.willpower else 0
    properties["arete"] = int(modal.arete) if modal.arete else 0
    properties["quintessence"] = int(modal.quintessence) if modal.quintessence else 0
    properties["rage"] = int(modal.rage) if modal.rage else 0
    properties["gnosis"] = int(modal.gnosis) if modal.gnosis else 0
    properties["blood_pool"] = int(modal.blood_pool) if modal.blood_pool else 0
    properties["conviction"] = int(modal.conviction) if modal.conviction else 0
    properties["faith"] = int(modal.faith) if modal.faith else 0

    ## VAMPIRE SPECIFIC #####################################################
    # If the character is a vampire, get the clan
    vampire_clan: str | None = None
    if char_class.lower() == "vampire":
        view = SelectClan(ctx.author)

        await ctx.send("Select a clan", view=view)
        await view.wait()
        vampire_clan = view.value

    properties["vampire_clan"] = vampire_clan

    ## START THE CHARGEN WIZARD #####################################################
    character_wizard = Wizard(ctx, quick_char=quick_char, properties=properties)
    await character_wizard.begin_chargen()
