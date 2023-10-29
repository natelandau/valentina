# FIXME: Progress towards using MongoDB

## New Features

-   [ ] On bot load, poll all character traits and update `custom` status and max value for traits in enums. This will keep database in-sync with the codebase.

## Migration

-   [x] macros
-   [ ] AWS
-   [ ] roll statistics on users, guilds, and characters
-   [x] character custom sections
-   [ ] roll thumbnails
-   [ ] roll probabilities
-   [x] mark custom traits as "is_custom"

## Cogs

-   [x] `developer` - re-post changelog

## Bot

-   [x] post changelog
-   [x] provision guilds on connect

## README

-   [ ] Update README.md to reflect mongodb and env variables
-   [ ] Remove the mongo section of .env

## Guilds

-   [x] post to error log
-   [ ] post to audit log
    -   [x] refactored to custom ctx object
    -   [ ] update all cogs/functions to use new ctx object

## utils

-   [ ] options
-   [ ] converters

## Other

-   [ ] Macros become a pydantic model with links to traits in DB
-   [ ] Review utils.errors for unused error types

## AWS

-   [ ] Migrate all calls to aws_svc
