"""Views for the character cog."""
import discord
from discord.ui import InputText, Modal, Select, View

from valentina.models.constants import VampClanList


class CustomSectionModal(Modal):
    """A modal for adding or editing a custom section."""

    def __init__(self, section_title: str | None = None, section_description: str | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.section_title = section_title
        self.section_description = section_description

        placeholder_name = self.section_title if self.section_title else "Name of the section"
        placeholder_description = (
            self.section_description if self.section_description else "Description of the section"
        )

        self.add_item(
            InputText(
                label="name",
                placeholder=placeholder_name,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder=placeholder_description,
                required=True,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.section_title = self.children[0].value
        self.section_description = self.children[1].value
        embed = discord.Embed(title="Custom Section Added")
        embed.add_field(name="Name", value=self.section_title)
        embed.add_field(name="Description", value=self.section_description)
        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        self.stop()


class BioModal(Modal):
    """A modal for entering a biography."""

    def __init__(self, current_bio: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.bio: str = None
        self.current_bio = current_bio

        placeholder = self.current_bio if self.current_bio else "Enter a biography"

        self.add_item(
            InputText(
                label="bio",
                value=placeholder,
                required=True,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Biography")
        self.bio = self.children[0].value
        embed.add_field(name="Bio", value=self.children[0].value)

        await interaction.response.send_message(embeds=[embed], ephemeral=True)
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

        embed = discord.Embed(title="Character Generation Review")
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


class SelectClan(View):
    """A dropdown for selecting a clan."""

    def __init__(self, author: discord.User) -> None:
        super().__init__()
        self.author = author
        self.value = ""

    @discord.ui.select(
        options=[discord.SelectOption(label=clan.value, value=clan.value) for clan in VampClanList],
        placeholder="Select a clan",
    )
    async def select_callback(self, select: Select, interaction: discord.Interaction) -> None:
        """Callback for the clan selection dropdown."""
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"You selected {select.values[0]}", ephemeral=True)
        if isinstance(select.values[0], str):
            self.value = select.values[0]
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Disables buttons for everyone except the user who created the embed."""
        return interaction.user.id == self.author.id
