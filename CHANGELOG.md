## v1.1.2 (2023-07-22)

### Fix

- **character**: compute age from chronicle date

## v1.1.1 (2023-07-22)

### Fix

- **character**: initital implementation of character age
- **character**: update xp cost and base skills

## v1.1.0 (2023-07-21)

### Feat

- **admin**: setting management (#24)

## v1.0.3 (2023-07-19)

### Fix

- **character**: add profile for characters
- **chronicle**: fix broken `chronicle delete` command
- **reference**: add thaumaturgy reference
- **logging**: improve logging

### Refactor

- combine all modals into single file

## v1.0.2 (2023-07-17)

### Fix

- **character**: fix calculating experience totals

## v1.0.1 (2023-07-17)

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

## v0.11.2 (2023-07-05)

### Fix

- **admin**: create on-demand database backups

## v0.11.1 (2023-07-03)

### Fix

- **chronicle**: find chapters by name
- **chronicle**: fix chronicle delete

## v0.11.0 (2023-07-02)

### Feat

- **diceroll**: reroll dice as needed

### Fix

- **chronicle**: fix update chapter
- **character**: allow claiming character with another claiemd
- **xp**: spend xp on custom traits
- **diceroll**: second trait required

## v0.10.3 (2023-07-02)

### Fix

- **diceroll**: cleanup dice roll embeds
- **chronicle**: send chronicle recaps via DM
- fix markdown error in trait update embed
- **chronicle**: delete chronicles

## v0.10.2 (2023-07-02)

### Fix

- **admin**: add uptime
- **chronicle**: add chronical overviews
- **help**: add chronicles to walkthrough
- **chronicle**: don't log confirmation embeds
- **database**: use ISO8601 for backup timestampes

## v0.10.1 (2023-07-02)

## v0.10.0 (2023-07-02)

### Feat

- **admin**: owners can shutdown the bot

## v0.9.0 (2023-07-02)

### Feat

- **chronicle**: add chronicle management (#17)

### Fix

- use `guild_svc` during bot connection
- **admin**: add database version to `ping`

## v0.8.3 (2023-07-01)

### Fix

- **reference**: add links to discipline reference
- **reference**: add reference info for magic and exp costs
- minor updates to confirmation embeds

## v0.8.2 (2023-07-01)

### Fix

- **admin**: use async routines to read log file
- **database**: automatic database backups
- **character**: add `security` trait
- minor text changes

## v0.8.1 (2023-06-30)

### Fix

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
- **xp**: break xp management into seperate command
- **help**: add a guide for understanding the bot

### Fix

- **character**: improve character sheet display
- **character**: add additional base traits
- **database**: add user who created character
- **xp**: add cool points to`/xp` command
- **help**: allow getting help for `help` command

### Refactor

- **character**: simplify properties during chargen

## v0.6.1 (2023-06-24)

### Fix

- **character**: add optional max value for custom traits

## v0.6.0 (2023-06-24)

### Feat

- **character**: add and manage custom sections (#11)

### Fix

- **character**: improve character sheet displays
- add cache for custom traits
- **macros**: add embed when no macros to list
- **characters**: remove duplicated message when no characters to list

## v0.5.1 (2023-06-21)

### Fix

- **help**: sort commands in help views

### Refactor

- remove unused code
- favor `ctx` in database services

## v0.5.0 (2023-06-21)

### Feat

- add macros for quick dice rolling (#10)

### Fix

- **database**: cleanup version management

## v0.4.0 (2023-06-20)

### Feat

- **diceroll**: roll traits by name (#9)
- custom traits (#8)

### Fix

- **character**: remove `music` ability
- minor text changes

## v0.3.2 (2023-06-18)

### Fix

- **config**: loosen capitalization rules for log levels

## v0.3.1 (2023-06-17)

### Fix

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
