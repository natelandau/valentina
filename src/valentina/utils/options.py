"""Reusable autocomplete options for cogs and commands."""

import discord
from discord.commands import OptionChoice

from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.utils.errors import NoClaimError


async def select_macro(ctx: discord.ApplicationContext) -> list[str]:
    """Populate a select list with a users' macros."""
    macros = []
    for macro in ctx.bot.user_svc.fetch_macros(ctx):  # type: ignore [attr-defined]
        if macro.name.lower().startswith(ctx.options["macro"].lower()):
            macros.append(f"{macro.name} ({macro.abbreviation})")
        if len(macros) >= MAX_OPTION_LIST_SIZE:
            break
    return macros


async def select_note(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the note option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except ValueError:
        return ["No active chronicle"]

    notes = []
    for note in ctx.bot.chron_svc.fetch_all_notes(ctx, chronicle=chronicle):  # type: ignore [attr-defined]
        if note.name.lower().startswith(ctx.options["note"].lower()):
            notes.append(f"{note.id}: {note.name}")
        if len(notes) >= MAX_OPTION_LIST_SIZE:
            break

    return notes


async def select_chapter(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the chapter option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except ValueError:
        return ["No active chronicle"]

    chapters = []
    for chapter in sorted(
        ctx.bot.chron_svc.fetch_all_chapters(ctx, chronicle=chronicle), key=lambda c: c.chapter  # type: ignore [attr-defined]
    ):
        if chapter.name.lower().startswith(ctx.options["chapter"].lower()):
            chapters.append(f"{chapter.chapter}: {chapter.name}")
        if len(chapters) >= MAX_OPTION_LIST_SIZE:
            break

    return chapters


async def select_npc(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the npc option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except ValueError:
        return ["No active chronicle"]

    npcs = []
    for npc in ctx.bot.chron_svc.fetch_all_npcs(ctx, chronicle=chronicle):  # type: ignore [attr-defined]
        if npc.name.lower().startswith(ctx.options["npc"].lower()):
            npcs.append(npc.name)
        if len(npcs) >= MAX_OPTION_LIST_SIZE:
            break

    return npcs


async def select_chronicle(ctx: discord.ApplicationContext) -> list[str]:
    """Generate a list of available chronicles."""
    chronicles = []
    for c in ctx.bot.chron_svc.fetch_all(ctx):  # type: ignore [attr-defined]
        if c.name.lower().startswith(ctx.options["chronicle"].lower()):
            chronicles.append(c.name)
        if len(chronicles) >= MAX_OPTION_LIST_SIZE:
            break

    return chronicles


async def select_custom_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available custom traits."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except NoClaimError:
        return ["No character claimed"]

    traits = []
    for trait in ctx.bot.char_svc.fetch_char_custom_traits(ctx, character):  # type: ignore [attr-defined]
        if trait.name.lower().startswith(ctx.options["trait"].lower()):
            traits.append(trait.name)
        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available traits."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except NoClaimError:
        return ["No character claimed"]

    traits = []
    for trait in ctx.bot.char_svc.fetch_all_character_traits(character, flat_list=True):  # type: ignore [attr-defined]
        if trait.lower().startswith(ctx.options["trait"].lower()):
            traits.append(trait)
        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break
    return traits


async def select_custom_section(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of the user's available custom sections."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except NoClaimError:
        return ["No character claimed"]

    sections = []
    for section in ctx.bot.char_svc.fetch_char_custom_sections(ctx, character):  # type: ignore [attr-defined]
        if section.title.lower().startswith(ctx.options["custom_section"].lower()):
            sections.append(section.title)
        if len(sections) >= MAX_OPTION_LIST_SIZE:
            break

    return sections


async def select_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters."""
    if (guild := ctx.interaction.guild) is None:
        return []

    # TODO: Check for chars associated with a user
    characters = ctx.bot.char_svc.fetch_all_characters(guild.id)  # type: ignore [attr-defined]
    chars = []
    for character in characters:
        char_id = character.id
        name = f"{character.name}"
        chars.append((name, char_id))

    name_search = ctx.value.casefold()

    found_chars = [
        OptionChoice(name, ident)
        for name, ident in sorted(chars)
        if name.casefold().startswith(name_search or "")
    ]

    if len(found_chars) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return found_chars
