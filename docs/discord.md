# Development Notes for Discord

Code snippets and notes to help you develop the Discord bot with pycord.

## Cogs

### Confirming actions

Use this pattern in any cog to ask for user confirmation before performing an action.

-   `hidden` makes the confirmation message ephemeral and viewable only by the author.
-   `audit` logs the confirmation in the audit log.

```python
from valentina.discord.views import confirm_action

@something.command()
async def do_something(self, ctx: ValentinaContext) -> None:

    is_confirmed, interaction, confirmation_embed = await confirm_action(
        ctx, title="Do something", hidden=True, audit=True
    )
    if not is_confirmed:
        return

    # Do something ...

    await interaction.edit_original_response(embed=confirmation_embed, view=None)
```
