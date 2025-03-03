## v3.4.0 (2025-03-03)

### Feat

- **character**: add `book` category to inventory items

### Fix

- **webui**: fix bug preventing throwing more than 5 dice

## v3.3.2 (2025-03-01)

### Fix

- **diceroll**: correctly compute rolled 1s as `-1` success (#230)

## v3.3.1 (2024-12-27)

### Fix

- **webui**: fix broken tabs on characters and campaign pages (#225)

## v3.3.0 (2024-12-27)

### Feat

- **webui**: set desperation and danger levels (#220)
- **webui**: reorder campaign book chapters (#219)
- **webui**: reorder campaign books (#218)
- **webui**: allow killing/reviving characters (#217)
- **webui**: add maintenance tasks to administration page (#216)
- **webui**: admin interface for storytellers (#215)
- add dictionary and auto-link terms (#214)
- **webui**: storytellers and owners can delete characters (#213)
- **webui**: upload and delete character images (#211)
- **webui**: add xp on user profile pages (#209)

### Fix

- **webui**: fix broken character creation (#224)
- **webui**: ui improvements (#222)
- **webui**: error showing full create character form (#210)
- **webui**: increase roll difficulties (#208)

### Refactor

- **webui**: simplify creating toasts (#223)
- **webui**: refactor htmx partials (#221)
- reuse code for character deletion (#212)

## v3.2.0 (2024-12-13)

### Feat

- **webui**: support Google or Cloudflare analytics (#207)

### Fix

- **webui**: improve logging of login errors (#206)

## v3.1.1 (2024-11-08)

### Fix

- **webui**: fix users with multiple guilds running valentina

## v3.1.0 (2024-11-08)

### Feat

- **webui**: fancy in-page transitions for forms (#201)
- **webui**: redesign homepage (#200)
- **webui**: add footer (#199)
- **webui**: add user profile and macro editing (#198)
- **webui**: storyteller quick character generation (#195)
- **webui**: edit campaigns (#194)
- **webui**: edit character inventory (#193)
- **webui**: edit character notes, biography, and custom sections (#192)
- **webui**: roll dice from character pages (#191)
- **webui**: edit character profile information (#189)
- **webui**: storytellers can update traits for any character (#188)
- **webui**: spend experience to upgrade characters (#187)
- **chargen**: correctly create werewolves and changelings (#186)
- **webui**: can spend freebie points after RNG chargen (#184)
- **webui**: quick roll new characters (#182)
- **webui**: allow creation of storyteller characters
- **webui**: storytellers can access every character (#181)

### Fix

- **webui**: players can view all player characters (#190)
- **webui**: rename discord channels when changes made in web (#179)
- **webui**: add favicons
- **webui**: pass x-forwarded-for header to hypercorn for logging behind reverse proxy

### Refactor

- **webui**: sync channel changes to discord (#197)
- improve run scripts (#196)
- constants (#183)
- webui can access guild and user permissions (#180)
- reorganize cli scripts
- reorganize discord models and views (#178)
- **webui**: reorganize file structure (#176)
- remove all naive datetimes

## v3.0.4 (2024-09-06)

### Fix

- **webui**: fix redirect error after logging in
- add VALENTINA_TRACE environment variable
- **webui**: work through cloudflared tunnel
- **webui**: add user guide to nav bar (#172)
- **webui**: use X-Forwarded-For when behind reverse proxy
- **webui**: fix insecure transport for oauth when behind reverse proxy

### Refactor

- cleanup env var trace and improve docstrings (#174)

## v3.0.0 (2024-08-16)

### Feat

- **webui**: initial web ui release (#171)

## v2.6.0 (2024-06-24)

### Feat

- **campaign**: add roll statistics (#162)
- campaign/character/roll commands must be run in channels (#161)
- attach notes to characters and campaign books (#160)
- **admin**: delete characters from database (#158)

### Fix

- **xp**: restrict xp spend to character channel (#164)
- **campaign**: improve `/campaign view`

### Refactor

- remove campaign channel migration (#159)

## v2.5.0 (2024-06-18)

### Feat

- **campaign**: set campaign from discord channel category (#157)

### Fix

- **changelog**: don't repost version on bot connect (#156)
- fewer errant line breaks in embeds (#155)
- **gameplay**: improve roll display (#154)
- fix bot missing required package

## v2.4.0 (2024-06-14)

### Feat

- **admin**: create and delete campaign channels (#152)
- **character**: rename characters with `/character rename` (#151)
- **campaign**: add books and chapter migration tool (#150)

### Fix

- **campaign**: improve campaign deletion (#153)
- fix bug where `/roll throw` was broken

## v2.3.0 (2024-06-09)

### Feat

- **character**: minimal release of inventory system (#148)
- **inventory**: minimal release of character inventory system
- **campaign**: chapters can be renumbered (#147)
- **campaign**: renumber chapters
- **character**: associate characters with campaigns (#145)
- **campaign**: add campaign specific channels (#141)

### Fix

- **user**: user_info now displays when no experience (#144)
- **chargen**: remove unused characters from db when cancelled (#137)
- **gameplay**: cleanup reroll buttons after 60 seconds
- autocomplete sorts traits alphabetically

### Refactor

- improve type hints (#146)

## v2.2.0 (2024-01-29)

### Feat

- **gameplay**: roll desperation dice (#120)
- **campaign**: track desperation and danger (#116)
- **admin**: change log level from discord  @natelandau (#113)

### Fix

- use `confz` for env variable parsing (#119)
- **logging**: correct printing of calling function names (#117)
- **campaign**: improve `/campaign view` (#115)
- actually post change log on bot connect (#114)
- **gameplay**: roll correct traits (#112)
- **gameplay**: fix bug rolling traits
- **character**: increase size of `/character list` (#111)
- **database**: wait for db before connecting bot

## v2.1.0 (2023-11-17)

### Feat

- **gameplay**: add `/gameplay damage` for damage effects
- add /github command to add/view issues  (#92)

### Refactor

- autopaginate text (#93)
- improve how random trait values are computed
- rename `options` to `autocomplete`

## v2.0.0 (2023-11-04)

### Feat

- migrate from Sqlite to MongoDB (#85)
- **chargen**: major overhaul of `/character create` (#78)

## v1.13.0 (2023-10-02)

### Feat

- **misc**: add random name generator `/name_gen` (#76)
- **character**: new chargen wizard with `character create`  (#75)

## v1.12.0 (2023-09-28)

### Feat

- **misc**: add `/server_info` command (#62)
- **character**: add `concept` to character profile (#59)
- **experience**: experience linked to players on a per campaign basis (#58)

### Fix

- **storyteller**: add 1 to all attributes in rng generator (#63)
- **misc**: clean up display of roll statistics (#61)
- **misc**: improve display of `/probabilities` (#60)
- **bot**: on connect print correct version to changelog channel

### Refactor

- **experience**: move xp logic to `GuildUser` object (#64)

## v1.11.0 (2023-09-17)

### Feat

- **storyteller**: storyteller characters now have images

### Fix

- **bot**: autoresponses only fire once on full words
- **admin**: add guild emoji as file or url
- **character**: alive characters no longer marked dead on character sheets
- fix error loading characters

### Refactor

- **character**: clean up `set_default_data_values`

## v1.10.0 (2023-09-16)

### Feat

- **character**: mark characters as dead
- **misc**: improve /changelog to specify versions (#57)

### Fix

- **gameplay**: add hints to use macros when rolling traits
- **admin**: add interaction user to check to `/admin settings`
- **storyteller**: update traits displays friendly error when trait not found
- **bot**: send changelog on connect (#56)
- **admin**: fix error in `/admin settings`

### Refactor

- **bot**: add newly joined guilds to the database
- **bot**: separate guild provisioning in `on_ready`
- **bot**: log additional steps in `on_ready`

## v1.9.0 (2023-09-10)

### Feat

- **bot**: add changelog channel configurable by admins
- **admin**: new setting manager with `/admin settings` (#55)
- add `/user_info` command

### Fix

- **character**: new `/character profile` command for nature,demeanor, etc
- **misc**: add footer to automated changelog posts
- **database**: create daily db backup at 0800 UTC
- **database**: close the connection before backup to ensure data integrity
- fix error when modal window title is too long

### Refactor

- **database**: remove unnecessary migration

## v1.8.0 (2023-09-05)

### Feat

- **bot**: respond to messages which `@` mention the bot
- **character**: move xp commands to `/character xp [command]`
- **storyteller**: add custom traits to storyteller characters
- **bot**: post changelog when new version is deployed (#54)

### Fix

- **admin**: reorganize admin commands to `/admin [noun] verb]`
- **developer**: reorganize developer commands to `/developer [noun] [verb]`
- **storyteller**: reorganize commands to `/storyteller [noun] [verb]`
- **character**: filter `/character list` by user or all
- **character**: reorganize commands to `/character [noun] [verb]`
- **character**: view sheets of any player character

## v1.7.0 (2023-09-03)

### Feat

- **character**: add and remove character images (#53)

## v1.6.0 (2023-08-27)

### Feat

- **character**: saved active characters replace character claims (#52)

### Fix

- **character**: fix character biographies
- **campaign**: fix typo breaking campaign notes
- **character**: improve display of character list
- **gameplay**: include url of thumbnail in log

### Refactor

- **admin**: reduce complexity of settings management (#51)

## v1.5.0 (2023-08-25)

### Feat

- **campaign**: setting to restrict campaign management to storytellers (#49)
- **storyteller**: update trait values for any character (#47)
- **storyteller**: create standard character via chargen wizard (#46)
- **admin**: review roll thumbnails and delete or recategorize (#44)
- **storyteller**: grant character cool points
- **storyteller**: grant character experience

### Fix

- **campaign**: rename `chronicles` to `campaigns` (#48)
- **admin**: add emoji to thumbnail review buttons (#45)
- **storyteller**: do not throw exception when rolling traits with no value (#43)
- **character**: fix error computing experience points (#42)
- **xp**: fix error computing experience points
- **bot**: improve audit logging (#41)
- improve display of probabilities and statistics
- **help**: improve user guide (#39)

### Refactor

- **character**: all trait values set within character object (#40)

## v1.4.0 (2023-08-17)

### Feat

- **admin**: clear probability results from database

### Fix

- **gameplay**: improve roll statistics display
- **developer**: migrate dev commands from admin cog (#37)
- **help**: improve interactive command help

### Refactor

- **database**: store character data in json (#38)

## v1.3.0 (2023-08-14)

### Feat

- **gameplay**: calculate roll probabilities (#35)
- **gameplay**: calculate and display roll statistics (#34)
- **misc**: view bot changelog with `/changelog`

### Fix

- **gameplay**: write user to db before logging roll (#36)
- **errors**: include traceback in error logs
- **errors**: improve error logging (#33)

## v1.2.0 (2023-08-09)

### Feat

- **storyteller**: add storyteller commands (#25)
- **storyteller**: add storyteller channel
- **guild**: create `player` and `storyteller` roles

### Fix

- **chronicle**: improve chronicle display
- **gameplay**: fix dicerolls
- **gameplay**: stop rerolls
- **character**: always show second page of character sheet
- **character**: compute age from chronicle date
- **character**: initital implementation of character age
- **character**: update xp cost and base skills

### Refactor

- **character**: improve character service (#32)
- improve database services (#31)

## v1.1.0 (2023-07-21)

### Feat

- **admin**: setting management (#24)

### Fix

- **character**: add profile for characters
- **chronicle**: fix broken `chronicle delete` command
- **reference**: add thaumaturgy reference
- **logging**: improve logging
- **character**: fix calculating experience totals

### Refactor

- combine all modals into single file

## v1.0.0 (2023-07-17)

### Feat

- **admin**: use prefix commands in DMs for bot admin commands
- **gameplay**: add coinflip option
- **admin**: add moderation commands

### Fix

- **character**: class specific traits
- **database**: improve database schema (#22)
- **character**: spending xp recognizes clan disciplines
- disallow thumbnails with bad http status
- **help**: improve help command

### Refactor

- favor methods on database objects
- reorganize package

## v0.12.0 (2023-07-10)

### Feat

- cleanup character creation and trait management (#21)

### Fix

- **character**: remove incorrect werewolf traits
- **admin**: create on-demand database backups
- **chronicle**: find chapters by name
- **chronicle**: fix chronicle delete

## v0.11.0 (2023-07-02)

### Feat

- **diceroll**: reroll dice as needed
- **admin**: owners can shutdown the bot

### Fix

- **chronicle**: fix update chapter
- **character**: allow claiming character with another claiemd
- **xp**: spend xp on custom traits
- **diceroll**: second trait required
- **diceroll**: cleanup dice roll embeds
- **chronicle**: send chronicle recaps via DM
- fix markdown error in trait update embed
- **chronicle**: delete chronicles
- **admin**: add uptime
- **chronicle**: add chronical overviews
- **help**: add chronicles to walkthrough
- **chronicle**: don't log confirmation embeds
- **database**: use ISO8601 for backup timestampes

## v0.9.0 (2023-07-02)

### Feat

- **chronicle**: add chronicle management (#17)

### Fix

- use `guild_svc` during bot connection
- **admin**: add database version to `ping`
- **reference**: add links to discipline reference
- **reference**: add reference info for magic and exp costs
- minor updates to confirmation embeds
- **admin**: use async routines to read log file
- **database**: automatic database backups
- **character**: add `security` trait
- minor text changes
- **admin**: improve clearing the cache

### Refactor

- remove stray debugging print statements

## v0.8.0 (2023-06-30)

### Feat

- **admin**: purge caches
- **character**: delete custom traits
- **admin**: add audit logging and settings management (#13)
- **character**: update existing custom sections

### Fix

- enqueue logs
- **character**: disallow negative experience
- **macros**: cancel macro creation now cancels creation
- **diceroll**: improve add thumbnail
- **diceroll**: improve roll displays
- **dicerolls**: remove animated gifs
- no longer crash with empty trait or macro descriptions
- **character**: fix bug preventing certain character sheets from displaying
- **diceroll**: randomize gifs

### Refactor

- **database**: rename database tables

## v0.7.0 (2023-06-25)

### Feat

- **character**: add clan to vampires
- **debug**: add `/debug tail` to allow viewing last lines of log
- **xp**: break xp management into separate command
- **help**: add a guide for understanding the bot

### Fix

- **character**: improve character sheet display
- **character**: add additional base traits
- **database**: add user who created character
- **xp**: add cool points to`/xp` command
- **help**: allow getting help for `help` command
- **character**: add optional max value for custom traits

### Refactor

- **character**: simplify properties during chargen

## v0.6.0 (2023-06-24)

### Feat

- **character**: add and manage custom sections (#11)
- add macros for quick dice rolling (#10)

### Fix

- **character**: improve character sheet displays
- add cache for custom traits
- **macros**: add embed when no macros to list
- **characters**: remove duplicated message when no characters to list
- **help**: sort commands in help views
- **database**: cleanup version management

### Refactor

- remove unused code
- favor `ctx` in database services

## v0.4.0 (2023-06-20)

### Feat

- **diceroll**: roll traits by name (#9)
- custom traits (#8)

### Fix

- **character**: remove `music` ability
- minor text changes
- **config**: loosen capitalization rules for log levels
- **character**: fix broken modal

### Refactor

- prepare for future database migrations (#7)

## v0.3.0 (2023-06-16)

## v0.2.0 (2023-06-16)

### Feat

- **deployment**: deploy with docker (#5)
- **character**: update character stats (#4)
- **character**: add characters and view character sheets (#3)
- **info**: add `health` command to show health levels
- **gameplay**: add `simple` dice roll command
- add database
- **debug**: add `reload_cogs` to `debug` cog
- **cog**: throw a diceroll

### Fix

- **diceroll**: show error when specifying illegal dice size
- **dicerolls**: remove default difficulty
- **bot**: add `owner_ids` to bot when instantiated

## v0.1.0 (2023-06-02)

### Feat

- **cogs**: add `/roll` command
- **bot**: initial bot scaffolding
