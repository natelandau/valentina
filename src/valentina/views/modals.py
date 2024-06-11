"""Modal windows for the application."""

import discord
from discord.ui import InputText, Modal

from valentina.constants import MAX_FIELD_COUNT, CharClass, EmbedColor
from valentina.models import CampaignBook, CampaignBookChapter, CampaignNote, CampaignNPC, Character
from valentina.views import ConfirmCancelButtons


class ChangeNameModal(Modal):
    """A modal for changing the name of a character."""

    def __init__(self, character: Character, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.character = character
        self.name = None

        self.add_item(
            InputText(
                label="First name",
                placeholder="Enter a first name for the character",
                value=self.character.name_first,
                style=discord.InputTextStyle.short,
                required=True,
            )
        )
        self.add_item(
            InputText(
                label="Last name",
                placeholder="Enter a last name for the character",
                value=self.character.name_last,
                style=discord.InputTextStyle.short,
                required=True,
            )
        )
        self.add_item(
            InputText(
                label="Nickname",
                placeholder="Enter a nickname for the character",
                value=self.character.name_nick or None,
                style=discord.InputTextStyle.short,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.first_name = self.children[0].value
        self.last_name = self.children[1].value
        self.nickname = self.children[2].value

        if self.first_name:
            self.character.name_first = self.first_name
        if self.last_name:
            self.character.name_last = self.last_name
        if self.nickname:
            self.character.name_nick = self.nickname

        await self.character.save()

        embed = discord.Embed(title="Name Updated", color=EmbedColor.SUCCESS.value)
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
                value=self.current_bio or None,
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


class BookModal(Modal):
    """A modal for campaign books."""

    def __init__(self, book: CampaignBook | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.description_short: str = ""
        self.description_long: str = ""

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=book.name if book else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description_short",
                placeholder="A short description for the book",
                value=book.description_short if book else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=500,
            )
        )
        self.add_item(
            InputText(
                label="description_long",
                placeholder="Long description of the book",
                value=book.description_long if book else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.description_short = self.children[1].value
        self.description_long = self.children[2].value

        embed = discord.Embed(title="Confirm Book", color=EmbedColor.INFO.value)
        embed.add_field(name="Book Name", value=self.name, inline=True)
        embed.add_field(name="Short Description", value=self.description_short, inline=True)
        embed.add_field(
            name="Book",
            value=(self.description_long[:MAX_FIELD_COUNT] + " ...")
            if len(self.description_long) > MAX_FIELD_COUNT
            else self.description_long,
            inline=False,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class ChapterModal(Modal):
    """A modal for adding chapters."""

    def __init__(self, chapter: CampaignBookChapter | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.description_short: str = ""
        self.description_long: str = ""

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=chapter.name if chapter else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description_short",
                placeholder="A short description for the chapter",
                value=chapter.description_short if chapter else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=500,
            )
        )
        self.add_item(
            InputText(
                label="description_long",
                placeholder="Write the chapter",
                value=chapter.description_long if chapter else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.description_short = self.children[1].value
        self.description_long = self.children[2].value

        embed = discord.Embed(title="Confirm Chapter", color=EmbedColor.INFO.value)
        embed.add_field(name="Chapter Name", value=self.name, inline=True)
        embed.add_field(name="Short Description", value=self.description_short, inline=True)
        embed.add_field(
            name="Chapter",
            value=(self.description_long[:MAX_FIELD_COUNT] + " ...")
            if len(self.description_long) > MAX_FIELD_COUNT
            else self.description_long,
            inline=False,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class InventoryItemModal(Modal):
    """A modal for managing inventory items."""

    def __init__(  # type: ignore [no-untyped-def]
        self,
        item_name: str | None = None,
        item_description: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.item_name = item_name
        self.item_description = item_description
        self.update_existing = bool(item_name)

        self.add_item(
            InputText(
                label="name",
                placeholder="Name of the section",
                value=self.item_name or None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Description of the section",
                value=self.item_description or None,
                style=discord.InputTextStyle.short,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.item_name = self.children[0].value
        self.item_description = self.children[1].value
        view = ConfirmCancelButtons(interaction.user)

        embed_title = "Update inventory" if self.update_existing else "Add item to inventory"
        embed_description = f"### {self.item_name}\n{self.item_description}"
        embed = discord.Embed(
            title=embed_title, description=embed_description, color=EmbedColor.DEFAULT.value
        )
        await interaction.response.send_message(embeds=[embed], ephemeral=True, view=view)

        await view.wait()
        if view.confirmed:
            self.confirmed = True
            embed_title = "Inventory updated" if self.update_existing else "Inventory item added"
            await interaction.edit_original_response(
                embeds=[
                    discord.Embed(
                        title=embed_title,
                        description=embed_description,
                        color=EmbedColor.SUCCESS.value,
                    )
                ]
            )
        if not view.confirmed:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class CustomSectionModal(Modal):
    """A modal for adding or editing a custom section."""

    def __init__(  # type: ignore [no-untyped-def]
        self,
        section_title: str | None = None,
        section_content: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.section_title = section_title
        self.section_content = section_content
        self.update_existing = bool(section_title)

        self.add_item(
            InputText(
                label="name",
                placeholder="Name of the section",
                value=self.section_title or None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Description of the section",
                value=self.section_content or None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        self.section_title = self.children[0].value
        self.section_content = self.children[1].value

        embed_title = "Custom Section Updated" if self.update_existing else "Custom Section Added"
        embed = discord.Embed(title=embed_title, color=EmbedColor.SUCCESS.value)
        embed.add_field(name="Name", value=self.section_title)
        embed.add_field(name="Description", value=self.section_content)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, delete_after=0)
        self.stop()


class MacroCreateModal(Modal):
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
            InputText(
                label="name",
                placeholder="Enter a name for the macro",
                value=self.name or None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="abbreviation",
                placeholder="Up to 4 character abbreviation",
                value=self.abbreviation or None,
                required=True,
                style=discord.InputTextStyle.short,
                max_length=4,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="A brief description of what this macro does",
                value=self.description or None,
                required=False,
                style=discord.InputTextStyle.long,
                max_length=600,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.abbreviation = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm macro creation", color=EmbedColor.INFO.value)
        embed.add_field(name="Macro Name", value=self.name)
        embed.add_field(name="Abbreviation", value=self.abbreviation)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )
        embed.add_field(name="Trait One", value=self.trait_one)
        embed.add_field(name="Trait Two", value=self.trait_two)
        await interaction.response.send_message(embeds=[embed], ephemeral=True, view=view)

        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        if not view.confirmed:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[
                    discord.Embed(title="Macro creation cancelled", color=EmbedColor.ERROR.value)
                ]
            )

        self.stop()


class NoteModal(Modal):
    """A modal for adding chapters."""

    def __init__(self, note: CampaignNote | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.name: str = ""
        self.description: str = ""

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the chapter",
                value=note.name if note else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Write a description for the chapter",
                value=note.description if note else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.description = self.children[1].value

        embed = discord.Embed(title="Confirm Note", color=EmbedColor.INFO.value)
        embed.add_field(name="Note Name", value=self.name, inline=True)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class NPCModal(Modal):
    """A modal for adding NPCs."""

    def __init__(self, npc: CampaignNPC | None = None, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.name: str = ""
        self.description: str = ""
        self.npc_class: str = ""
        self.confirmed: bool = False

        self.add_item(
            InputText(
                label="name",
                placeholder="Enter a name for the NPC",
                value=npc.name if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="npc_class",
                placeholder="Enter a class for the npc (e.g. 'vampire', 'mortal')",
                value=npc.npc_class if npc else None,
                required=True,
                style=discord.InputTextStyle.short,
            )
        )
        self.add_item(
            InputText(
                label="description",
                placeholder="Enter a description for the NPC",
                value=npc.description if npc else None,
                required=True,
                style=discord.InputTextStyle.long,
                max_length=1900,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        self.name = self.children[0].value
        self.npc_class = self.children[1].value
        self.description = self.children[2].value

        embed = discord.Embed(title="Confirm NPC", color=EmbedColor.INFO.value)
        embed.add_field(name="NPC Name", value=self.name, inline=True)
        embed.add_field(name="NPC Class", value=self.npc_class, inline=True)
        embed.add_field(
            name="Description",
            value=(self.description[:MAX_FIELD_COUNT] + " ...")
            if len(self.description) > MAX_FIELD_COUNT
            else self.description,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()


class ProfileModal(Modal):
    """Update a character's profile."""

    def __init__(self, character: Character, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False
        self.character: Character = character
        self.results: dict[str, str] = {
            "auspice": "",
            "creed_name": "",
            "breed": "",
            "concept_name": "",
            "demeanor": "",
            "essence": "",
            "generation": "",
            "nature": "",
            "sire": "",
            "tradition": "",
            "tribe": "",
        }

        self.add_item(
            InputText(
                label="concept",
                value=self.character.concept_name.capitalize()
                if self.character.concept_name
                else None,
                placeholder="Enter a concept",
                required=False,
                style=discord.InputTextStyle.short,
                custom_id="concept_name",
            )
        )

        if self.character.char_class == CharClass.VAMPIRE:
            self.add_item(
                InputText(
                    label="generation",
                    value=self.character.generation,
                    placeholder="Enter a generation (integer, e.g. 13 or 3)",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="generation",
                )
            )

            self.add_item(
                InputText(
                    label="sire",
                    value=self.character.sire,
                    placeholder="Name of your sire",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="sire",
                )
            )

        if self.character.char_class == CharClass.MAGE:
            self.add_item(
                InputText(
                    label="essence",
                    value=self.character.essence,
                    placeholder="Your essence",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="essence",
                )
            )
            self.add_item(
                InputText(
                    label="tradition",
                    value=self.character.tradition,
                    placeholder="Your tradition",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="tradition",
                )
            )

        if self.character.char_class == CharClass.WEREWOLF:
            self.add_item(
                InputText(
                    label="breed",
                    value=self.character.breed,
                    placeholder="Your breed",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="breed",
                )
            )
            self.add_item(
                InputText(
                    label="tribe",
                    value=self.character.tribe,
                    placeholder="Your tribe",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="tribe",
                )
            )
            self.add_item(
                InputText(
                    label="auspice",
                    value=self.character.auspice,
                    placeholder="Your auspice",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="auspice",
                )
            )

        if self.character.char_class == CharClass.HUNTER:
            self.add_item(
                InputText(
                    label="creed_name",
                    value=self.character.creed_name.capitalize()
                    if self.character.creed_name
                    else None,
                    placeholder="Your creed",
                    required=False,
                    style=discord.InputTextStyle.short,
                    custom_id="creed_name",
                )
            )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for the modal."""
        view = ConfirmCancelButtons(interaction.user)
        for c in self.children:
            self.results[c.custom_id] = c.value

        embed = discord.Embed(title="Confirm Profile", color=EmbedColor.INFO.value)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.confirmed:
            self.confirmed = True
            await interaction.delete_original_response()
        else:
            self.confirmed = False
            await interaction.edit_original_response(
                embeds=[discord.Embed(title="Cancelled", color=EmbedColor.ERROR.value)]
            )

        self.stop()
