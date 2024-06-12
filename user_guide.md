# Valentina Noir User Guide

This guide will help you understand and use Valentina Noir, a bot that manages characters and gameplay for a highly customized version of Vampire the Masquerade. Here's what you'll find inside:

1. **Introduction**
2. **Core Concepts**
3. **Character Creation & Management**
4. **Gameplay**
5. **Campaigns**
6. **Storyteller Features**
7. **Other Features**
8. **Roles in Valentina Noir**
9. **Troubleshooting & FAQ**

## 1. INTRODUCTION

Valentina Noir assists in managing role-playing sessions, providing easy access to character stats and dice rolling. Valentina's rules are highly customized. The major differences from the published Vampire the Masquerade game include:

-   **Dice Rolling:** Dice are rolled as a pool of D10s with a set difficulty. The number of successes determines the outcome:
    -   `< 0` successes: Botch
    -   `0` successes: Failure
    -   `> 0` successes: Success
    -   `> dice pool` successes: Critical success
-   **Special Rolls:** Rolled ones count as -1 success, and rolled tens count as 2 successes.
-   **Cool Points**: Additional rewards worth 10xp each.
-   **Experience**: Experience is granted to players for use on any of their characters within a specific campaign.

Valentina uses Discord "slash" commands to manage characters and gameplay. To type any command, type `/` into a the Discord message field.

For interactive help, run `/help commands` to see a list of available commands.

## 2. CORE CONCEPTS

Valentina Noir revolves around three core concepts:

-   **Characters**: Player characters managed in Valentina allow for quick dice rolling, XP spending, and character updates.
-   **Campaigns**: Storylines with multiple chapters, characters, NPCs, and notes, spanning multiple gaming sessions.
-   **Gameplay**: The actual game, where you roll dice and play using your character.

## 3. CHARACTER CREATION & MANAGEMENT

### Creating a Character

-   Use `/character add` to add a new character you've already created by hand.
-   User `/character create` to create use a RNG guided character creation process.
-   **IMPORTANT**: If using `/character add`, create your character on paper before entering it into Valentina.
-   **Post creation:** Don't worry if you make a mistake or the section on your sheet doesn't appear during character generation.You can easily rename your character, add/update traits, abilities, custom sections, and a biography as needed.

### Working with characters

Each character has a specific channel within their associated campaign. This channel is where you can interact with your character, roll dice, and manage their traits. Use commands like `/roll`, `/xp`, and `/character` in the character's campaign channel to manage and play with your character.

In some circumstances, you may want to transfer ownership of a character to another user. To do so, use `/character transfer` and specify the character name and the user to transfer to.

### Updating Your Character

-   **Attributes and Abilities**: In Valentina, attributes, abilities, skills, backgrounds, etc. are all call `traits`. Use `/character trait [add/update/delete]` to manage your character's traits.
-   **Images**: You can attach images to you character using `/character image [add/delete]`. Images are displayed on the character sheet.
-   **Custom Sections**: Use `/character section [add/update/delete]` to add custom sections to your character sheet. This is useful for adding additional information that doesn't fit into the standard character sheet such as inventory, spells, etc.
-   **Biography**: Use `/character bio update` to add or edit a biography for your character.
-   **Profile**: Use `/character profile update` to manage your character's concept, and class specific items such as clan, sire, tribe, etc.
-   **Spending XP**: Use `/xp spend` to spend XP and increase your character's traits.

## 4. GAMEPLAY

### Macros

**What is a Macro?** In Valentina Noir, a macro is a custom shortcut that you can create to simplify complex dice rolls. Macros are tied to users, not characters, meaning you can use the same macro regardless of which character is active.

For example, if you often need to roll for _perception_ and _alertness_, you can create a macro called `pa` that combines these stats into a single roll. Instead of typing computing the number of dice yourself, you can simply use `/roll macro pa`, and Valentina Noir will execute the roll for you.

Here's how you can work with macros:

-   **Creating a Macro**: Use `/macro create` to define a new macro. You'll need to specify the name and the associated stats or commands.
-   **Using a Macro**: Once created, you can roll a macro using `/roll macro <macro_name>`. The system will compute the dice based on the skills associated with the macro.
-   **Note:** Using Macros: Macros are tied to users, not characters, and can be used across characters.

Macros are a powerful tool to enhance your gaming experience, allowing for quicker and more streamlined gameplay.

### During Gameplay

-   **Roll Dice**: Use `/roll` for various types of rolls, including stats, traits, macros, D10s, or arbitrary dice.
-   **Create Campaign NPCs**: As you meet an important NPC, take a note of them with `/campaign npc create`.
-   **Add Campaign Notes**: Keep track of important information by creating notes during gameplay with `/campaign note create`.
-   **Determine damage**: Use `/gameplay damage [damage]` to determine the effects of damage.

### Dice Rolling

Rolling dice is a core part of gameplay. Valentina Noir provides the following commands to roll dice:

-   **Rolling D10s**: Use `/roll throw` to roll any number of D10s against an optional difficulty (default is 6).
-   **Rolling Traits**: Use `/roll traits <trait_name> <trait_name>` to roll a trait. For example, `/roll traits strength brawl` will compute the correct dice to roll based on your character.
-   **Rolling a Macro**: Use `/roll macro <macro_name>` to roll a macro. For example, `/roll macro pa` will roll the macro `pa` that you created earlier.
-   **Rolling Arbitrary Dice**: Use `/roll <dice>` to roll arbitrary dice. For example, `/roll 3d6` will roll 3 six-sided dice.

The core mechanics of gameplay in Valentina Noir differ from the published Vampire the Masquerade game. Unless otherwise specified, all rolls are made as a pool of D10s with a set difficulty. The pool is determined by the number of dots for the two traits.

The number of _successes_ is determined by counting each d10.

-   **10s**: Each 10 counts as 2 successes
-   **1s**: Each 1 counts as -2 success
-   **Successes**: Each die >= difficulty counts as 1 success

The outcome of the role is defined as:

-   **Critical Success:** More successes than dice rolled
-   **Success:** At least one success after all dice are tallied
-   **Failure:** Zero successes after all dice are tallied
-   **Botch:** Negative successes after all dice are tallied

### After Gameplay

-   Add or spend experience points using `/xp`.

> NOTE: Valentina treats experience differently than most TTRPGs. Instead of granting XP to a specific character, XP is granted to a player. This allows players to spend XP on any of their characters within a specific campaign.

## 5. CAMPAIGNS

Campaigns are the backbone of your role-playing adventure in Valentina Noir. They span across multiple gaming sessions and help in organizing the story, keeping track of characters and events, and providing a cohesive narrative structure. Regularly updating chapters and making use of NPCs and notes ensures that information is not lost in between gaming sessions.

Campaigns are organized into books and each book can have multiple chapters.

When a campaign is created, channels will be created for each book and character. This allows for easy organization and management of the campaign. Add notes in the chapter channels to keep track of important information. Players can easily roll dice and manage their characters by using those commands in their character's campaign channel.

### Creating and Managing Campaigns

-   **Creating**: Use `/campaign create` to create a new campaign, setting the foundation for your campaign.
-   **Setting Active**: Use `/campaign set_active` to set a campaign as active, allowing you to add chapters, NPCs, and notes to it.

### During Gameplay

-   **Creating NPCs**: NPCs are vital to enriching the story. Create them during gameplay using `/campaign npc create`.
-   **Adding Notes**: Keep track of important information by creating notes during gameplay with `/campaign note create`.

### After Gameplay

-   **Updating Chapters**: After each gameplay session, update the chapters using `/campaign chapter create`. This helps in maintaining the continuity and progression of the story.
-   **Viewing**: Use commands like `/campaign list`, `/campaign view`, `/campaign chapter list`, and `/campaign npc list` to view and manage the campaigns, chapters, NPCs, and notes.

## 6. STORYTELLER FEATURES

Storytellers have access to many features that help in managing the game. These include:

-   **Private Channels**: Storytellers can create a private channel that is not viewable by players. This allows them to manage the game without revealing information to the players.
-   **NPCs**: Storytellers can create NPCs and then quickly roll dice for their traits
    -   `/storyteller create_story_char` to create an NPC with full control over trait values
    -   `/storyteller create_rng_char` to quickly create an NPC with randomized trait values
-   **Transfer Characters**: Use `/storyteller transfer_character` to transfer a character from one user to another.

## 7. OTHER FEATURES

The core features of Valentina Noir are covered in the previous sections. These additional features are also available:

-   **Help**: Use `/help` to get help on various topics, including commands, traits, and macros.
-   **Coinflip**: Use `/coinflip` to flip a coin.
-   **Roll Probabilities**: Use `/probability` to see the probability of rolling a certain number of successes.
-   **Roll Statistics**: Use `/reference statistics` to see the diceroll statistics for a guild, user, or character.
-   **Reference Information**: Use `/reference` for information on various topics such as health, magic, disciplines, and more.
-   **Adding Roll Result Images**: Use `/roll upload_thumbnail` to add an image or animated gif to a roll result.
-   **Interact with Github**: Use `/github` to interact with the Valentina Noir GitHub repository. You can view open issues or add new ones right here on Discord.

## 8. ROLES IN VALENTINA NOIR

In Valentina Noir, users can have one of three distinct roles, each with its own responsibilities and capabilities. Understanding these roles helps in managing and participating in the game effectively.

### Admin

The `Admin` is responsible for overall management and configuration of the Valentina Noir system within the Discord server. This role typically includes:

-   **Setting Up**: Configuring the system, managing permissions, and ensuring that everything is running smoothly.
-   **User Management**: Assigning roles to users, such as designating Storytellers or managing player access.
-   **Troubleshooting**: Handling technical issues, updates, and coordinating with the Valentina Noir support if needed.
-   **Managing Settings**: Use `/admin settings` to access various administrative settings.

### Storyteller

The `Storyteller` is the game master, guiding the narrative and controlling non-player characters (NPCs), events, and the overall direction of the game. Responsibilities include:

-   **Narrative Control**: Creating and managing Campaigns, chapters, NPCs, and notes.
-   **Game Management**: Rolling dice for NPCs, controlling game flow, and ensuring fair play.
-   **Player Interaction**: Engaging with players, managing in-game events, and making judgment calls.
-   **Commands**: Various commands like `/storyteller character create` and `/storyteller roll_traits` are available to manage the game.

### Player

`Players` are the participants in the game, controlling individual characters and interacting with the story as it unfolds. As a player, you will:

-   **Character Management**: Create, claim, and manage your character, including stats, traits, and abilities.
-   **Gameplay Participation**: Engage in gameplay by rolling dice, using macros, and making decisions for your character.
-   **Collaboration**: Work with other players and the Storyteller to create an engaging and immersive story.
-   **Commands**: Utilize commands like `/character create`, `/roll`, and `/xp` to interact with the game.

## 9. TROUBLESHOOTING & FAQ

This section provides solutions to common problems and answers to frequently asked questions. If you encounter an issue not covered here, please refer to the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina) for support.

**Q: How do I update the value of a trait after my character is created?** **A:** Use `/character update` to update the value of an existing trait. However, depending on your guild settings you may not have permissions to do so. If this occurs, please contact your storyteller or an admin.

**Q: I found a bug. How do I report it?** **A:** Use `/github issues add` to create a new issue on the Valentina Noir GitHub repository. Or visit the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina) and create a new issue.

**Q: I have a feature request. Who do I tell?** **A:** Please file an issue on the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina). Provide as much detail as possible on the feature you would like to see.

**Q: Can I play multiple characters at once?** **A:** You can create multiple characters, but you may only have a single character active at a time. To set a character as active, use `/character set_active` and specify the character name.

**Q: How do I become a Storyteller or Admin?** **A:** Roles like Storyteller and Admin are typically assigned by the server owner or existing Admins. Speak with them if you are interested in taking on one of these roles.

**Q: Can I use Valentina Noir for other role-playing games besides Vampire the Masquerade?** **A:** Valentina Noir is specifically designed for a highly customized version of Vampire the Masquerade. While some features might be applicable to other games, it may not fully support them.

### Need More Help?

If you have a question or issue not covered here, please consult the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina) or reach out to the community for assistance.
