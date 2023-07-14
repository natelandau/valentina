"""Views for the character cog."""
import discord
from discord.ui import InputText, Modal

from valentina.models.constants import EmbedColor


class CustomSectionModal(Modal):
    """A modal for adding or editing a custom section."""

    def __init__(self, section_title: str | None = None, section_description: str | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.section_title = section_title
        self.section_description = section_description
        self.update_existing = bool(section_title)

        self.add_item(
            InputText(
                label="name",
                placeholder="Name of the section",
                value=self.section_title if self.section_title else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Description of the section",
                value=self.section_description if self.section_description else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.section_title = self.children[0].value
        self.section_description = self.children[1].value

        embed_title = "Custom Section Updated" if self.update_existing else "Custom Section Added"
        embed = discord.Embed(title=embed_title, color=EmbedColor.SUCCESS.value)
        embed.add_field(name="Name", value=self.section_title)
        embed.add_field(name="Description", value=self.section_description)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)
        self.stop()


class BioModal(Modal):
    """A modal for entering a biography."""

    def __init__(self, current_bio: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.bio: str = None
        self.current_bio = current_bio

        self.add_item(
            InputText(
                label="bio",
                placeholder="Enter a biography",
                value=self.current_bio if self.current_bio else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Biography Updated", color=EmbedColor.SUCCESS.value)
        self.bio = self.children[0].value
        embed.add_field(name="Bio", value=self.children[0].value)

        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)
        self.stop()


class CharGenModal(Modal):
    """A modal creating characters."""

    def __init__(self, char_class: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.char_class = char_class
        self.humanity: str = None
        self.willpower: str = None
        self.blood_pool: str = None
        self.arete: str = None
        self.quintessence: str = None
        self.gnosis: str = None
        self.rage: str = None
        self.conviction: str = None
        self.faith: str = None

        self.add_item(
            InputText(
                label="Willpower",
                style=discord.InputTextStyle.short,
                required=True,
                placeholder="Enter a number",
                max_length=2,
            )
        )
        self.add_item(
            InputText(
                label="Humanity",
                style=discord.InputTextStyle.short,
                required=True,
                placeholder="Enter a number",
                max_length=2,
            )
        )
        match char_class.lower():
            case "mage":
                self.add_item(
                    InputText(
                        label="Arete",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    InputText(
                        label="Quintessence",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "werewolf":
                self.add_item(
                    InputText(
                        label="Rage",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    InputText(
                        label="Gnosis",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "vampire":
                self.add_item(
                    InputText(
                        label="Blood Pool",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "hunter":
                self.add_item(
                    InputText(
                        label="Conviction",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    InputText(
                        label="Faith",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.willpower = self.children[0].value
        self.humanity = self.children[1].value

        embed = discord.Embed(title="Character Generation Review", color=EmbedColor.INFO.value)
        embed.add_field(name="Willpower", value=self.children[0].value)
        embed.add_field(name="Humanity", value=self.children[1].value)

        if self.char_class.lower() == "mage":
            embed.add_field(name="Arete", value=self.children[2].value)
            embed.add_field(name="Quintessence", value=self.children[3].value)
            self.arete = self.children[2].value
            self.quintessence = self.children[3].value

        elif self.char_class.lower() == "werewolf":
            embed.add_field(name="Rage", value=self.children[2].value)
            embed.add_field(name="Gnosis", value=self.children[3].value)
            self.rage = self.children[2].value
            self.gnosis = self.children[3].value

        elif self.char_class.lower() == "vampire":
            embed.add_field(name="Blood Pool", value=self.children[2].value)
            self.blood_pool = self.children[2].value

        elif self.char_class.lower() == "hunter":
            embed.add_field(name="Conviction", value=self.children[2].value)
            self.conviction = self.children[2].value
            embed.add_field(name="Faith", value=self.children[3].value)
            self.faith = self.children[3].value

        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        self.stop()
