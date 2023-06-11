"""Manage character claims."""

import discord
from loguru import logger

from valentina import char_svc, user_svc


async def claim_character(ctx: discord.ApplicationContext, char_id: int) -> None:
    """Claim a character to a user."""
    if not user_svc.is_cached(ctx.guild.id, ctx.user.id) and not user_svc.is_in_db(
        ctx.guild.id, ctx.user.id
    ):
        user_svc.create(ctx.guild.id, ctx.user)

    character = char_svc.fetch_by_id(ctx.guild.id, char_id)

    if char_svc.is_char_claimed(ctx.guild.id, char_id):
        await ctx.send(f"{character.first_name} already claimed.")
        return
    if char_svc.user_has_claim(ctx.guild.id, ctx.user.id):
        await ctx.send("You already have a claimed character.")
        return

    char_svc.add_claim(ctx.guild.id, char_id, ctx.user.id)
    logger.info(f"CLAIM: {character.first_name} claimed by {ctx.author.name}.")
    await ctx.send(f"Character {character.first_name} claimed.")
