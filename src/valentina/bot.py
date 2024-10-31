"""This module contains the Valentina bot."""

import discord

from valentina.__version__ import __version__
from valentina.discord.bot import Valentina
from valentina.utils import ValentinaConfig

bot = Valentina(
    debug_guilds=[int(g) for g in ValentinaConfig().guilds.split(",")],
    intents=discord.Intents.all(),
    owner_ids=[int(o) for o in ValentinaConfig().owner_ids.split(",")],
    command_prefix="∑",  # Effectively remove the command prefix by setting it to 'sigma' which no one will ever use
    version=__version__,
)
