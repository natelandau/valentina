"""One time migration from sqlite to mongodb."""
from datetime import datetime

from loguru import logger

from valentina.constants import (
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
    RollResultType,
    TraitCategory,
)
from valentina.models import (
    Campaign,
    CampaignChapter,
    CampaignExperience,
    CampaignNote,
    CampaignNPC,
    Character,
    CharacterSheetSection,
    CharacterTrait,
    GlobalProperty,
    Guild,
    GuildChannels,
    GuildPermissions,
    GuildRollResultThumbnail,
    RollStatistic,
    User,
)
from valentina.models.sqlite_models import Campaign as SqliteCampaign
from valentina.models.sqlite_models import CampaignChapter as SqliteCampaignChapter
from valentina.models.sqlite_models import CampaignNote as SqliteCampaignNote
from valentina.models.sqlite_models import CampaignNPC as SqliteCampaignNPC
from valentina.models.sqlite_models import Character as SqliteCharacter
from valentina.models.sqlite_models import CustomSection as SqliteCustomSection
from valentina.models.sqlite_models import DatabaseVersion as SQLVersion
from valentina.models.sqlite_models import Guild as SqliteGuild
from valentina.models.sqlite_models import GuildUser as SqliteUser
from valentina.models.sqlite_models import RollStatistic as SqliteRollStatistic
from valentina.models.sqlite_models import RollThumbnail as SqliteRollThumbnail
from valentina.utils.helpers import get_max_trait_value


class Migrate:
    """One time migration from sqlite to mongodb."""

    def __init__(self, config: dict) -> None:
        """Initialize."""
        self.config = config
        self.campaign_map: list[tuple[int, str]] = []

    @staticmethod
    async def _migrate_version() -> None:
        """Migrate version."""
        property_document = GlobalProperty()
        await property_document.insert()

        for v in SQLVersion.select().order_by(SQLVersion.id.asc()):
            property_document.versions.append(v.version)

        await property_document.save()

    @staticmethod
    async def _migrate_guilds() -> None:
        """Migrate guilds."""
        # Get all guilds
        guilds = SqliteGuild.select()
        for sqlguild in guilds:
            # Create permissions object
            permissions = GuildPermissions(
                manage_traits=PermissionsManageTraits(
                    sqlguild.data.get("permissions_edit_trait", None)
                ),
                grant_xp=PermissionsGrantXP(sqlguild.data.get("permissions_edit_xp", None)),
                manage_campaigns=PermissionManageCampaign(
                    sqlguild.data.get("permissions_manage_campaigns", None)
                ),
                kill_character=PermissionsKillCharacter(
                    sqlguild.data.get("permissions_kill_character", None)
                ),
            )

            channels = GuildChannels(
                audit_log=sqlguild.data.get("audit_log_channel_id", None),
                changelog=sqlguild.data.get("changelog_channel_id", None),
                error_log=sqlguild.data.get("error_log_channel_id", None),
                storyteller=sqlguild.data.get("storyteller_channel_id", None),
            )

            # Get roll thumbnails
            roll_thumbnails = [
                GuildRollResultThumbnail(
                    url=thumbnail.url,
                    roll_type=RollResultType[thumbnail.roll_type],
                    user=SqliteUser.get(SqliteUser.id == thumbnail.user).user,
                    date_created=datetime.strptime(thumbnail.created, "%Y-%m-%d %H:%M:%S%z"),
                )
                for thumbnail in SqliteRollThumbnail.select().where(
                    SqliteRollThumbnail.guild == sqlguild
                )
            ]

            # Create mongo guild object
            mongo_guild = Guild(
                id=sqlguild.id,
                name=sqlguild.name,
                changelog_posted_version=sqlguild.data.get("changelog_posted_version", None),
                date_created=datetime.strptime(sqlguild.created, "%Y-%m-%d %H:%M:%S%z"),
                permissions=permissions,
                channels=channels,
                roll_result_thumbnails=roll_thumbnails,
            )

            # insert guild into mongo
            await mongo_guild.insert()
            logger.debug(f"MIGRATION: Insert guild `{mongo_guild.name}` into mongo")

    async def _migrate_campaigns(self) -> None:
        """Migrate campaigns."""
        for sqlcampaign in SqliteCampaign.select():
            # fetch the guild object
            guild = await Guild.get(sqlcampaign.guild.id)

            mongo_campaign = Campaign(
                guild=sqlcampaign.guild.id,
                name=sqlcampaign.name if sqlcampaign.name else "",
                date_created=datetime.strptime(sqlcampaign.created, "%Y-%m-%d %H:%M:%S%z"),
                date_modified=datetime.strptime(sqlcampaign.created, "%Y-%m-%d %H:%M:%S%z"),
                description=sqlcampaign.description if sqlcampaign.description else "",
                date_in_game=datetime.strptime(sqlcampaign.current_date, "%Y-%m-%d %H:%M:%S"),
            )
            await mongo_campaign.insert()

            # associate the campaign with the guild
            guild.campaigns.append(mongo_campaign)
            if sqlcampaign.is_active:
                guild.active_campaign = mongo_campaign

            await guild.save()

            # Create mapping to be used for user experience
            self.campaign_map.append((sqlcampaign.id, str(mongo_campaign.id)))

            # Add chapters, npcs, and notes
            for sqlchapter in SqliteCampaignChapter.select().where(
                SqliteCampaignChapter.campaign == sqlcampaign
            ):
                chapter = CampaignChapter(
                    description_long=sqlchapter.description,
                    description_short=sqlchapter.short_description,
                    name=sqlchapter.name,
                    number=sqlchapter.chapter_number,
                    date_created=datetime.strptime(sqlchapter.created, "%Y-%m-%d %H:%M:%S%z"),
                )
                mongo_campaign.chapters.append(chapter)

            for npc in SqliteCampaignNPC.select().where(SqliteCampaignNPC.campaign == sqlcampaign):
                new_npc = CampaignNPC(
                    description=npc.description, name=npc.name, npc_class=npc.npc_class
                )
                mongo_campaign.npcs.append(new_npc)

            for note in SqliteCampaignNote.select().where(
                SqliteCampaignNote.campaign == sqlcampaign
            ):
                new_note = CampaignNote(description=note.description, name=note.name)
                mongo_campaign.notes.append(new_note)
            await mongo_campaign.save()

            logger.debug(f"MIGRATION: Insert campaign `{mongo_campaign.name}` into mongo")

    async def _migrate_users(self) -> None:
        for sqluser in SqliteUser.select():
            # build base user object
            mongo_user = User(
                id=sqluser.user,
                name=sqluser.data.get("display_name", None),
                date_created=datetime.strptime(
                    sqluser.data.get("modified", None), "%Y-%m-%d %H:%M:%S%z"
                ),
                lifetime_cool_points=sqluser.data.get("lifetime_cool_points", None),
                lifetime_experience=sqluser.data.get("lifetime_experience", None),
            )
            await mongo_user.insert()

            # Add guilds
            mongo_user.guilds.append(sqluser.guild.id)

            # Add campaign experience
            for old, new in self.campaign_map:
                if sqluser.data.get(f"{old}_experience", None):
                    xp_object = CampaignExperience(
                        xp_current=sqluser.data.get(f"{old}_experience", None),
                        cool_points=sqluser.data.get(f"{old}_total_cool_points", None),
                        xp_total=sqluser.data.get(f"{old}_total_experience", None),
                    )
                    mongo_user.campaign_experience[new] = xp_object

            # Save user
            await mongo_user.save()
            logger.debug(f"MIGRATION: Insert user `{mongo_user.name}` into mongo")

    @staticmethod
    async def _migrate_characters() -> None:
        """Migrate characters."""
        for sqlchar in SqliteCharacter.select():
            # Grab the user object
            owned_by_user = await User.get(sqlchar.owned_by.user)
            creator_user = await User.get(sqlchar.created_by.user)

            character = Character(
                char_class_name=sqlchar.char_class.name if sqlchar.char_class else "",
                date_created=datetime.strptime(sqlchar.created, "%Y-%m-%d %H:%M:%S%z"),
                date_modified=datetime.strptime(
                    sqlchar.data.get("modified", None), "%Y-%m-%d %H:%M:%S%z"
                ),
                guild=sqlchar.guild.id,
                images=list(sqlchar.data["images"]) if sqlchar.data.get("images", False) else [],
                is_alive=sqlchar.data.get("is_alive", None),
                name_first=sqlchar.data.get("first_name", None),
                name_last=sqlchar.data.get("last_name", None),
                name_nick=sqlchar.data.get("nickname", None),
                type_chargen=sqlchar.data.get("chargen_character", False),
                type_debug=sqlchar.data.get("debug_character", False),
                type_developer=sqlchar.data.get("developer_character", False),
                type_player=sqlchar.data.get("player_character", False),
                type_storyteller=sqlchar.data.get("storyteller_character", False),
                user_creator=creator_user.id,
                user_owner=owned_by_user.id,
                bio=sqlchar.data.get("bio", None),
                age=sqlchar.data.get("age", None),
                auspice=sqlchar.data.get("auspice", None),
                breed=sqlchar.data.get("breed", None),
                clan_name=sqlchar.clan.name if sqlchar.clan else "",
                concept_name=sqlchar.data.get("concept_db", None),
                creed_name=sqlchar.data.get("creed", None),
                demeanor=sqlchar.data.get("demeanor", None),
                dob=datetime.strptime(sqlchar.data["date_of_birth"], "%Y-%m-%d %H:%M:%S")
                if sqlchar.data.get("date_of_birth", None)
                else None,
                essence=sqlchar.data.get("essence", None),
                generation=sqlchar.data.get("generation", None),
                nature=sqlchar.data.get("nature", None),
                sire=sqlchar.data.get("sire", None),
                tradition=sqlchar.data.get("tradition", None),
                tribe=sqlchar.data.get("tribe", None),
            )
            await character.insert()

            # Mark characters as active
            if sqlchar.data.get("is_active", None):
                owned_by_user.active_characters[str(character.guild)] = character

            # Add character to user character list
            owned_by_user.characters.append(character)
            await owned_by_user.save()

            # Migration custom sections
            for section in SqliteCustomSection.select().where(
                SqliteCustomSection.character == sqlchar
            ):
                character.sheet_sections.append(
                    CharacterSheetSection(title=section.title, content=section.description)
                )

            # Assign trait values
            all_trait_categories = [
                TraitCategory[trait.category.name]
                for trait in sqlchar.traits_list
                if trait.category.name != "ADVANTAGES"
            ]
            all_categories = sorted(set(all_trait_categories), key=lambda x: x.value.order)

            for category in all_categories:
                for trait in sqlchar.traits_list:
                    if trait.category.name == category.name:
                        # Check if the trait is custom
                        if trait.name not in TraitCategory[
                            category.name
                        ].value.COMMON and trait.name not in getattr(
                            TraitCategory[category.name].value, character.char_class_name
                        ):
                            is_custom = True
                        else:
                            is_custom = False

                        # Create the new trait
                        new_trait = CharacterTrait(
                            category_name=trait.category.name,
                            character=str(character.id),
                            name=trait.name,
                            value=sqlchar.get_trait_value(trait),
                            is_custom=is_custom,
                            display_on_sheet=True,
                            max_value=get_max_trait_value(trait.name, trait.category.name),
                        )
                        await new_trait.insert()

                        # Add the trait to the character
                        character.traits.append(new_trait)

            # save the character
            await character.save()
            logger.debug(f"MIGRATION: Insert character `{character.name}` into mongo")

    @staticmethod
    async def _migrate_roll_statistics() -> None:
        """Migrate roll statistics."""
        for stat in SqliteRollStatistic.select():
            try:
                sqlcharacter = stat.character if stat.character else None
            except SqliteCharacter.DoesNotExist:
                sqlcharacter = None

            if sqlcharacter:
                character = await Character.find_one(
                    Character.name_first == sqlcharacter.data.get("first_name", "")
                )
            else:
                character = None

            new_stat = RollStatistic(
                user=SqliteUser.get(SqliteUser.id == stat.user).user,
                guild=stat.guild.id,
                character=str(character.id) if character else None,
                result=RollResultType[stat.result],
                pool=stat.pool,
                difficulty=stat.difficulty,
                date_rolled=datetime.strptime(stat.date_rolled, "%Y-%m-%d %H:%M:%S%z"),
            )
            await new_stat.insert()

    async def do_migration(self) -> None:
        """Perform the migration."""
        if not await GlobalProperty.find().to_list():
            logger.info("MIGRATION: Migrate Version")
            await self._migrate_version()
        else:
            logger.info("MIGRATION: Version already migrated")

        if not await Guild.find().to_list():
            logger.info("MIGRATION: Migrate Guilds")
            await self._migrate_guilds()
        else:
            logger.info("MIGRATION: Guilds already migrated")

        if not await Campaign.find().to_list():
            logger.info("MIGRATION: Migrate Campaigns")
            await self._migrate_campaigns()
        else:
            logger.info("MIGRATION: Campaigns already migrated")

        if not await User.find().to_list():
            logger.info("MIGRATION: Migrate Users")
            await self._migrate_users()
        else:
            logger.info("MIGRATION: Users already migrated")

        if not await Character.find().to_list():
            logger.info("MIGRATION: Migrate Characters")
            await self._migrate_characters()
        else:
            logger.info("MIGRATION: Characters already migrated")

        if not await RollStatistic.find().to_list():
            logger.info("MIGRATION: Migrate RollStatistic")
            await self._migrate_roll_statistics()
        else:
            logger.info("MIGRATION: RollStatistic already migrated")
