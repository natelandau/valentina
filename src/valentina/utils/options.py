"""Reusable autocomplete options for cogs and commands."""

import discord
from discord.commands import OptionChoice

from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.models.db_tables import CharacterClass, Trait, TraitCategory, VampireClan
from valentina.utils import errors


async def select_chapter(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the chapter option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveChronicleError:
        return ["No active chronicle"]

    chapters = []
    for chapter in sorted(
        ctx.bot.chron_svc.fetch_all_chapters(chronicle=chronicle), key=lambda c: c.chapter  # type: ignore [attr-defined]
    ):
        if chapter.name.lower().startswith(ctx.options["chapter"].lower()):
            chapters.append(f"{chapter.chapter}: {chapter.name}")
        if len(chapters) >= MAX_OPTION_LIST_SIZE:
            break

    return chapters


async def select_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters."""
    if (guild := ctx.interaction.guild) is None:
        return []

    # TODO: Check for chars associated with a user
    characters = ctx.bot.char_svc.fetch_all_player_characters(guild.id)  # type: ignore [attr-defined]
    all_chars = []
    for character in characters:
        char_id = character.id
        name = f"{character.name}"
        all_chars.append((name, char_id))

    name_search = ctx.value.casefold()

    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search or "")
    ]

    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options


async def select_char_class(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available character classes."""
    classes = []
    for char_class in CharacterClass.select().order_by(CharacterClass.name.asc()):
        if char_class.name.lower().startswith(ctx.options["char_class"].lower()):
            classes.append(char_class.name)
        if len(classes) >= MAX_OPTION_LIST_SIZE:
            break

    return classes


async def select_char_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common and custom traits for a character."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except errors.NoClaimError:
        return ["No character claimed"]

    # Discord option can be either "trait" or "trait_one"
    if "trait" in ctx.options:
        argument = ctx.options["trait"]
    elif "trait_one" in ctx.options:
        argument = ctx.options["trait_one"]

    traits = []
    for t in character.traits_list:
        if t.name.lower().startswith(argument.lower()):
            traits.append(t.name)

        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_char_trait_two(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common and custom traits for a character."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except errors.NoClaimError:
        return ["No character claimed"]

    traits = []
    for t in character.traits_list:
        if t.name.lower().startswith(ctx.options["trait_two"].lower()):
            traits.append(t.name)

        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_chronicle(ctx: discord.ApplicationContext) -> list[str]:
    """Generate a list of available chronicles."""
    chronicles = []
    for c in ctx.bot.chron_svc.fetch_all(ctx):  # type: ignore [attr-defined]
        if c.name.lower().startswith(ctx.options["chronicle"].lower()):
            chronicles.append(c.name)
        if len(chronicles) >= MAX_OPTION_LIST_SIZE:
            break

    return chronicles


async def select_custom_section(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of the user's available custom sections."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except errors.NoClaimError:
        return ["No character claimed"]

    sections = []
    for section in character.custom_sections:
        if section.title.lower().startswith(ctx.options["custom_section"].lower()):
            sections.append(section.title)
        if len(sections) >= MAX_OPTION_LIST_SIZE:
            break

    return sections


async def select_custom_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available custom traits."""
    try:
        character = ctx.bot.char_svc.fetch_claim(ctx)  # type: ignore [attr-defined]
    except errors.NoClaimError:
        return ["No character claimed"]

    traits = []
    for trait in character.custom_traits:
        if trait.name.lower().startswith(ctx.options["trait"].lower()):
            traits.append(trait.name)
        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_country(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available countries."""
    options = [
        OptionChoice("United States", "us"),
        OptionChoice("African", "ng,ke,za"),
        OptionChoice("Arabia", "da,mn,ta,jo,tn,ma,eg"),
        OptionChoice("Asian", "cn,jp,kr"),
        OptionChoice("Brazil", "br"),
        OptionChoice("France", "fr"),
        OptionChoice("Germany", "de"),
        OptionChoice("Greece", "gr"),
        OptionChoice("India", "in"),
        OptionChoice("Italy", "it"),
        OptionChoice("Mexico", "mx"),
        OptionChoice("Russia", "ru"),
        OptionChoice("Scaninavia", "nl,se,no,dk,fi"),
        OptionChoice("South American", "ar,cl,co,pe,ve"),
        OptionChoice("Spain", "es"),
        OptionChoice("Turkey", "tr"),
    ]

    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a country."
        return [OptionChoice(f"Too many options to display. {instructions}", "")]

    return options


async def select_macro(ctx: discord.ApplicationContext) -> list[OptionChoice]:
    """Populate a select list with a users' macros."""
    options = [
        OptionChoice(f"{macro.name} {macro.abbreviation}", str(macro.id))
        for macro in ctx.bot.macro_svc.fetch_macros(ctx.interaction.guild.id, ctx.interaction.user.id)  # type: ignore [attr-defined]
        if macro.name.lower().startswith(ctx.options["macro"].lower())
    ]

    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options


async def select_note(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the note option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveChronicleError:
        return ["No active chronicle"]

    notes = []
    for note in ctx.bot.chron_svc.fetch_all_notes(chronicle):  # type: ignore [attr-defined]
        if note.name.lower().startswith(ctx.options["note"].lower()):
            notes.append(f"{note.id}: {note.name}")
        if len(notes) >= MAX_OPTION_LIST_SIZE:
            break

    return notes


async def select_npc(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the npc option."""
    try:
        chronicle = ctx.bot.chron_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveChronicleError:
        return ["No active chronicle"]

    npcs = []
    for npc in ctx.bot.chron_svc.fetch_all_npcs(chronicle=chronicle):  # type: ignore [attr-defined]
        if npc.name.lower().startswith(ctx.options["npc"].lower()):
            npcs.append(npc.name)
        if len(npcs) >= MAX_OPTION_LIST_SIZE:
            break

    return npcs


async def select_storyteller_character(ctx: discord.ApplicationContext) -> list[OptionChoice]:
    """Generate a list of the user's available storyteller characters."""
    if (guild := ctx.interaction.guild) is None:
        return []

    characters = ctx.bot.char_svc.fetch_all_storyteller_characters(guild_id=guild.id)  # type: ignore [attr-defined]

    all_chars = []
    for character in characters:
        char_id = character.id
        name = f"{character.full_name} ({character.char_class.name})"
        all_chars.append((name, char_id))

    name_search = ctx.value.casefold()

    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search or "")
    ]

    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options


async def select_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common traits."""
    # Discord option can be either "trait" or "trait_one"
    if "trait" in ctx.options:
        argument = ctx.options["trait"]
    elif "trait_one" in ctx.options:
        argument = ctx.options["trait_one"]

    traits = []
    for t in Trait.select().order_by(Trait.name.asc()):
        if t.name.lower().startswith(argument.lower()):
            traits.append(t.name)

        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_trait_two(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common traits."""
    traits = []

    for t in Trait.select().order_by(Trait.name.asc()):
        if t.name.lower().startswith(ctx.options["trait_two"].lower()):
            traits.append(t.name)

        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break

    return traits


async def select_trait_category(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available trait categories."""
    categories = []
    for category in TraitCategory.select().order_by(TraitCategory.name.asc()):
        if category.name.lower().startswith(ctx.options["category"].lower()):
            categories.append(category.name)
        if len(categories) >= MAX_OPTION_LIST_SIZE:
            break

    return categories


async def select_vampire_clan(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available vampire clans."""
    clans = []
    for clan in VampireClan.select().order_by(VampireClan.name.asc()):
        if clan.name.lower().startswith(ctx.options["vampire_clan"].lower()):
            clans.append(clan.name)
        if len(clans) >= MAX_OPTION_LIST_SIZE:
            break

    return clans
