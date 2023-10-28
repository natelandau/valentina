# FIXME: Progress towards using MongoDB

## New Features

-   [ ] Poll all character traits and update `custom` status for traits in enums

## Possible Schema

-   Add each trait to a "traits" collection and link the traits back to characters and macros. If there is no chance of two traits sharing the same name this is likely more complicated than it's worth
    -   Pros:
        -   common trait information (category, max_value, etc.) can be stored in one place
        -   linking traits to characters and macros won't rely on the trait name as a key allowing names to be changed without breaking links and allowing multiple traits with the same name
    -   Cons:
        -   more complex queries
        -   more complex migrations
        -   Traits can be added by editing Enums

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

-   [x] options
-   [ ] converters

## Other

-   [ ] Macros become a pydantic model with links to traits in DB
-   [ ] Review utils.errors for unused error types

## AWS

-   [ ] Migrate all calls to aws_svc
