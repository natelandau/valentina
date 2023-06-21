"""Modal windows for the application."""
import discord

from valentina.views import ConfirmCancelButtons


class MacroCreateModal(discord.ui.Modal):
    """A modal for adding macros."""

    def __init__(self, trait_one: str, trait_two: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.name: str = None
        self.abbreviation: str = None
        self.description: str = ""
        self.confirmed: bool = False
        self.trait_one = trait_one
        self.trait_two = trait_two

        self.add_item(
            discord.ui.InputText(
                label="name",
                placeholder="Enter a name for the macro",
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="abbreviation",
                placeholder="Up to 4 character abbreviation",
                required=True,
                style=discord.InputTextStyle.short,
                max_length=4,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="description",
                placeholder="A brief description of what this macro does",
                required=False,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.abbreviation = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm macro creation")
        embed.add_field(name="Macro Name", value=self.name)
        embed.add_field(name="Abbreviation", value=self.abbreviation)
        embed.add_field(name="Description", value=self.description)
        embed.add_field(name="Trait One", value=self.trait_one)
        embed.add_field(name="Trait Two", value=self.trait_two)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, view=view)

        await view.wait()
        if view.confirmed:
            self.confirmed = True

        self.stop()
