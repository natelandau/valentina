"""Present errors to the user."""

import discord


async def present_error(
    ctx: discord.ApplicationContext,
    error: str,
    *fields: tuple[str, str],
    footer: str = None,
) -> None:
    """Display an error in a nice embed.

    Args:
        ctx: The Discord context for sending the response.
        error: The error messages to display.
        fields (list): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        footer (str): Footer text to display.
    """
    embed = discord.Embed(title="ERROR", colour=0xFF0000)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

    embed.description = error

    for field in fields:
        name, value = field
        embed.add_field(name=name, value=value, inline=False)

    if footer:
        embed.set_footer(text=footer)

    await ctx.respond(embed=embed, ephemeral=True)
