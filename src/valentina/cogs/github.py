# mypy: disable-error-code="valid-type"
"""Github cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from github import Auth, Github
from github.Repository import Repository
from loguru import logger

from valentina.constants import GithubIssueLabels, LogLevel
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils import ValentinaConfig, errors
from valentina.views import present_embed


class GithubCog(commands.Cog):
    """Github Cog commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot
        self.repo: Repository | None = None

    async def fetch_github_repo(self) -> Repository:
        """Fetch the github repo."""
        if self.repo:
            return self.repo

        token = ValentinaConfig().github_token
        repo_name = ValentinaConfig().github_repo

        if not token or not repo_name:
            msg = "Github"
            raise errors.ServiceDisabledError(msg)

        try:
            auth = Auth.Token(token)
            g = Github(auth=auth)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error fetching github repo: {e}")
            msg = "Github"
            raise errors.ServiceDisabledError(msg) from e

        self.repo = g.get_repo(repo_name)
        return self.repo

    github = discord.SlashCommandGroup("github", "Interact with the Valentina Noir Github repo")
    issues = github.create_subgroup("issues", "Interact with Github issues")

    @issues.command(name="list", description="List open issues")
    async def issue_list(self, ctx: ValentinaContext) -> None:
        """List open Github issues."""
        ctx.log_command("github issues list", LogLevel.DEBUG)
        repo = await self.fetch_github_repo()
        open_issues = repo.get_issues(state="open")
        for issue in open_issues:
            logger.info(issue)

        if open_issues.totalCount == 0:
            await ctx.send("No open issues")
            return

        issue_list = "\n- ".join(
            [
                f"**[{issue.title}]({issue.html_url})** `(#{issue.number})`"
                for issue in sorted(open_issues, key=lambda x: x.number)
            ],
        )
        await present_embed(
            ctx,
            f"Listing {open_issues.totalCount} Open Github Issues",
            description=f" - {issue_list}\n\n> - Use `/github issues get <issue number>` for details on a specific issue\n> - Use `/github issues add` to add a new issue\n> - View [all issues on Github]({repo.html_url}/issues)",
            level="info",
            footer="",
        )

    @issues.command(name="get", description="Get details for a specific issue")
    async def issue_get(self, ctx: ValentinaContext, issue_number: int) -> None:
        """Get details for a specific Github issue."""
        ctx.log_command(f"github issues get {issue_number}", LogLevel.DEBUG)
        repo = await self.fetch_github_repo()
        issue = repo.get_issue(number=issue_number)
        await present_embed(
            ctx,
            f"Github Issue #{issue.number}",
            description=f"### [{issue.title}]({issue.html_url})\n{issue.body}",
            level="info",
        )

    @issues.command(name="add", description="Add a new issue")
    async def issue_add(
        self,
        ctx: ValentinaContext,
        title: Option(str, name="title", description="Title of the issue", required=True),
        description: Option(
            str, name="description", description="Description of the issue", required=True
        ),
        type_of_issue: Option(
            str,
            name="type",
            description="Type of issue",
            required=True,
            choices=[x.value for x in GithubIssueLabels],
        ),
    ) -> None:
        """Add a new Github issue."""
        ctx.log_command(f"github issues add {title} {description} {type_of_issue}", LogLevel.DEBUG)
        repo = await self.fetch_github_repo()
        issue = repo.create_issue(title=title, body=description, labels=[type_of_issue])
        await present_embed(
            ctx,
            "Issue Created",
            description=f"### [{issue.title}]({issue.html_url})\n{description}",
            level="info",
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(GithubCog(bot))
