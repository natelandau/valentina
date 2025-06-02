"""Model for error handling."""

import traceback

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import EmbedColor
from valentina.discord.views import user_error_embed
from valentina.utils import errors


class ErrorReporter:
    """Error handler reports errors to channels and logs."""

    def __init__(self) -> None:
        """Initialize the error reporter."""
        self.bot: commands.Bot = None
        self.channel: discord.TextChannel = None

    @staticmethod
    def _handle_known_exceptions(  # noqa: C901
        ctx: discord.ApplicationContext,
        error: Exception,
    ) -> tuple[str | None, str | None, bool]:
        """Handle known exceptions and return user message, log message, and traceback flag.

        Args:
            ctx (discord.ApplicationContext): The context in which the command was called.
            error (Exception): The exception that was raised.

        Returns:
            tuple[str | None, str | None, bool]: The user message, log message, and a boolean to show traceback.
        """
        user_msg = None
        log_msg = None
        show_traceback = False

        # Logged and reported to users but not shown in traceback
        if isinstance(
            error,
            commands.errors.MissingAnyRole
            | commands.errors.MissingRole
            | commands.MissingPermissions
            | commands.NotOwner,
        ):
            user_msg = "Sorry, you don't have permission to run this command!"
            log_msg = f"COMMAND: `{ctx.user.display_name}` tried to run `/{ctx.command}` without the correct permissions"

        # Reported to users but suppressed from logs and traceback
        if isinstance(
            error,
            errors.ValidationError
            | errors.ChannelTypeError
            | errors.NotEnoughExperienceError
            | errors.NoExperienceInCampaignError
            | errors.URLNotAvailableError
            | errors.ServiceDisabledError
            | errors.S3ObjectExistsError
            | errors.TraitExistsError
            | errors.TraitAtMaxValueError
            | errors.TraitAtMinValueError
            | errors.NotEnoughFreebiePointsError,
        ):
            user_msg = str(error)

        if isinstance(error, FileNotFoundError):
            user_msg = (
                "Sorry, I couldn't find that file. This is likely a bug and has been reported."
            )
            log_msg = f"ERROR: `{ctx.user.display_name}` tried to run `/{ctx.command}` and a file was not found"
            show_traceback = True

        if isinstance(error, errors.MissingConfigurationError):
            user_msg = "Sorry, something went wrong. This has been reported."
            log_msg = f"ERROR: `{ctx.user.display_name}` tried to run `/{ctx.command}` and a configuration variable was not found"
            show_traceback = True

        if isinstance(error, errors.NoCharacterClassError):
            user_msg = "Sorry, something went wrong. This has been reported"
            log_msg = f"ERROR: `{ctx.user.display_name}` tried to run `/{ctx.command}` and a character class was not found"
            show_traceback = True

        if isinstance(error, errors.MessageTooLongError):
            user_msg = "Message too long to send. This is a bug has been reported."
            log_msg = "ERROR: Message too long to send. Check the logs for the message."
            show_traceback = True

        if isinstance(error, errors.BotMissingPermissionsError):
            user_msg = "Sorry, I don't have permission to run this command!"
            log_msg = f"ERROR: Bot tried to run `/{ctx.command}` without the correct permissions"
            show_traceback = True

        if isinstance(error, errors.NoCTXError):
            user_msg = "Sorry, something went wrong. This has been reported."
            log_msg = "ERROR: No context provided"
            show_traceback = True

        if isinstance(error, commands.BadArgument):
            user_msg = "Invalid argument provided"

        if isinstance(error, commands.NoPrivateMessage):
            user_msg = "Sorry, this command can only be run in a server!"

        if isinstance(error, discord.errors.DiscordServerError):
            # There's nothing we can do about these
            user_msg = "Discord server error detected"
            log_msg = "SERVER: Discord server error detected"
            show_traceback = True

        return user_msg, log_msg, show_traceback

    async def report_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        """Report an error to the error log channel and application log.

        Args:
            ctx (Union[discord.ApplicationContext, discord.Interaction]): The context of the command.
            error (Exception): The exception to be reported.

        Returns:
            None
        """
        user_msg = None
        log_msg = None
        show_traceback = False

        error = getattr(error, "original", error)
        respond = (
            ctx.respond
            if isinstance(ctx, discord.ApplicationContext)
            else (ctx.followup.send if ctx.response.is_done() else ctx.response.send_message)
        )

        user_msg, log_msg, show_traceback = self._handle_known_exceptions(ctx, error)

        # Handle unknown exceptions
        if not user_msg and not log_msg and not show_traceback:
            user_msg = "An error has occurred. This is a bug and has been reported."
            log_msg = f"A `{error.__class__.__name__}` error has occurred. Check the logs for more information."
            show_traceback = True

        # Send the messages
        if user_msg:
            embed_message = user_error_embed(ctx, user_msg, str(error))  # type: ignore [arg-type]
            try:
                await respond(embed=embed_message, ephemeral=True, delete_after=15)
            except discord.HTTPException:
                await respond(
                    embed=user_error_embed(
                        ctx,  # type: ignore [arg-type]
                        "Message too long to send",
                        "This is a bug has been reported",
                    ),
                    ephemeral=True,
                    delete_after=15,
                )
                log_msg = f"NEW ERROR: Message too long to send. Check the logs for the message.\n\nOriginal error: {error.__class__.__name__}"
                show_traceback = True

        if log_msg:
            log_method = logger.opt(exception=error).error if show_traceback else logger.warning
            log_method(log_msg)
            embed = await self.error_log_embed(ctx, log_msg, error)
            await ctx.post_to_error_log(embed, error)  # type: ignore [attr-defined]

        if show_traceback:
            logger.opt(exception=error).error(f"ERROR: {error}")

    @staticmethod
    async def error_log_embed(
        ctx: discord.ApplicationContext | discord.Interaction,
        msg: str,
        error: Exception,
    ) -> discord.Embed:
        """Create an embed for errors."""
        description = f"{msg}\n"
        description += "```"
        description += "\n".join(traceback.format_exception(error))
        description += "```"

        # If we can, we use the command name to try to pinpoint where the error
        # took place. The stack trace usually makes this clear, but not always!
        if isinstance(ctx, discord.ApplicationContext):
            command_name = ctx.command.qualified_name.upper()
        else:
            command_name = "INTERACTION"

        error_name = type(error).__name__

        embed = discord.Embed(
            title=f"{command_name}: {error_name}",
            description=description,
            color=EmbedColor.INFO.value,
            timestamp=discord.utils.utcnow(),
        )

        if ctx.guild is not None:
            guild_name = ctx.guild.name
            guild_icon = ctx.guild.icon or ""
        else:
            guild_name = "DM"
            guild_icon = ""

        embed.set_author(name=f"{ctx.user.name} on {guild_name}", icon_url=guild_icon)

        return embed


reporter = ErrorReporter()
