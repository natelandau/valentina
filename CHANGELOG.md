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
