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
