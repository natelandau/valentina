"""Views for the character cog."""
import discord


class BioModal(discord.ui.Modal):
    """A modal for entering a biography."""

    def __init__(self, current_bio: str, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.bio: str = None
        self.current_bio = current_bio

        placeholder = self.current_bio if self.current_bio else "Enter a biography"

        self.add_item(
            discord.ui.InputText(
                label="bio",
                placeholder=placeholder,
                required=True,
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Modal Results")
        self.bio = self.children[0].value
        embed.add_field(name="Bio", value=self.children[0].value)

        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        self.stop()


class CharGenModal(discord.ui.Modal):
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

        self.add_item(
            discord.ui.InputText(
                label="Willpower",
                style=discord.InputTextStyle.short,
                required=True,
                placeholder="Enter a number",
                max_length=2,
            )
        )
        self.add_item(
            discord.ui.InputText(
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
                    discord.ui.InputText(
                        label="Arete",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    discord.ui.InputText(
                        label="Quintessence",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "werewolf":
                self.add_item(
                    discord.ui.InputText(
                        label="Rage",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
                self.add_item(
                    discord.ui.InputText(
                        label="Gnosis",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "vampire":
                self.add_item(
                    discord.ui.InputText(
                        label="Blood Pool",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )
            case "hunter":
                self.add_item(
                    discord.ui.InputText(
                        label="Conviction",
                        style=discord.InputTextStyle.short,
                        required=True,
                        placeholder="Enter a number",
                        max_length=2,
                    )
                )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        embed = discord.Embed(title="Modal Results")
        self.willpower = self.children[0].value
        self.humanity = self.children[1].value
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

        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        self.stop()
