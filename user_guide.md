#Welcome to the Valentina Noir Guide!
This guide will help you understand and use Valentina Noir, a tool that manages characters and gameplay for a highly customized version of Vampire the Masquerade. Here's what you'll find inside:

1. Introduction
2. Core Concepts
3. Character Creation & Management
4. Gameplay
5. Chronicles
6. Storyteller Commands
7. Roles in Valentina Noir
8. Troubleshooting & FAQ

## 1. INTRODUCTION

Valentina Noir assists in managing role-playing sessions, providing easy access to character stats and dice rolling. The major differences from the published Vampire the Masquerade game include:

-   **Dice Rolling:** Dice are rolled as a pool of D10s with a set difficulty. The number of successes determines the outcome:
    -   `< 0` successes: Botch
    -   `0` successes: Failure
    -   `> 0` successes: Success
    -   `> dice pool` successes: Critical success
-   **Special Rolls:** Rolled ones count as -1 success, and rolled tens count as 2 successes.
-   **Cool Points**: Additional rewards worth 10xp each.

Valentina uses Discord "slash" commands to manage characters and gameplay. to type any command type `/` into a the Discord message field.

For interactive help, run `/help` commands to see a list of available commands.

## 2. CORE CONCEPTS

Valentina Noir revolves around three core concepts:

-   **Characters**: The main focus, with stats, traits, and abilities. They can be claimed by users for gameplay.
-   **Chronicles**: Storylines with multiple chapters, NPCs, and notes, spanning multiple gaming sessions.
-   **Gameplay**: The actual game, where you roll dice and play using your character.
-   **Storyteller Commands**: Commands for the Storyteller to manage the game.

## 3. CHARACTER CREATION & MANAGEMENT

### Creating a Character

-   Use `/character create` to create a character sheet.
-   **IMPORTANT**: Create your character on paper before entering it into Valentina.
-   **Post creation:** Don't worry if you make a mistake or the section on your sheet doesn't appear during character generation.You can easily add/update traits, abilities, custom sections, and a biography as needed.

### Managing Your Character

-   **Claiming**: Use `/character claim` to claim a character for rolling dice and making updates.
-   **Unclaiming**: Use `/character unclaim` to allow another user to claim the character.
-   **Adding new information**: Use `/character add` to add new traits, abilities, custom sections, and a biography.
-   **Updating information**: Use `/character update` to update existing traits, abilities, custom sections, and a biography.
-   **Spending XP**: Use `/xp` to spend XP and increase your character's stats.

## 4. GAMEPLAY

### Before Gameplay

-   Create characters using `/character create`.
-   Claim a character using `/character claim`.
-   Create macros for diceroll shortcuts using `/macro create`.

**What is a Macro?**
In Valentina Noir, a macro is a custom shortcut that you can create to simplify complex dice rolls or frequently used commands. Macros are tied to users, not characters, meaning you can use the same macro across different characters.

For example, if you often need to roll for perception and alertness, you can create a macro called `pa` that combines these stats into a single roll. Instead of typing out the full command each time, you can simply use `/roll macro pa`, and Valentina Noir will execute the roll for you.

Here's how you can work with macros:

-   **Creating a Macro**: Use `/macro create` to define a new macro. You'll need to specify the name and the associated stats or commands.
-   **Using a Macro**: Once created, you can roll a macro using `/roll macro <macro_name>`. The system will compute the dice based on the skills associated with the macro.
-   **Note:** Using Macros: Macros are tied to users, not characters, and can be used across characters.

Macros are a powerful tool to enhance your gaming experience, allowing for quicker and more streamlined gameplay.

### During Gameplay

-   **Roll Dice**: Use `/roll` for various types of rolls, including stats, traits, macros, D10s, or arbitrary dice.
-   **Create Chronicle NPCs**: As you meet an important NPC, take a note of them with `/chronicle npc create`.
-   **Add Chronicle Notes**: Keep track of important information by creating notes during gameplay with `/chronicle note create`.

### After Gameplay

-   Add or spend experience points using `/xp`.
-   Unclaim your character using `/character unclaim`.

## 5. CHRONICLES

Chronicles are the backbone of your role-playing adventure in Valentina Noir. They span across multiple gaming sessions and help in organizing the story, keeping track of characters and events, and providing a cohesive narrative structure. Regularly updating chapters and making use of NPCs and notes ensures that information is not lost in between gaming sessions.

### Creating and Managing Chronicles

-   **Creating**: Use `/chronicle create` to create a new chronicle, setting the foundation for your campaign.
-   **Setting Active**: Use `/chronicle set_active` to set a chronicle as active, allowing you to add chapters, NPCs, and notes to it.

### During Gameplay

-   **Creating NPCs**: NPCs are vital to enriching the story. Create them during gameplay using `/chronicle npc create`.
-   **Adding Notes**: Keep track of important information by creating notes during gameplay with `/chronicle note create`.

### After Gameplay

-   **Updating Chapters**: After each gameplay session, update the chapters using `/chronicle chapter create`. This helps in maintaining the continuity and progression of the story.
-   **Viewing**: Use commands like `/chronicle list`, `/chronicle view`, `/chronicle chapter list`, and `/chronicle npc list` to view and manage the chronicles, chapters, NPCs, and notes.

## 6. STORYTELLER COMMANDS

Storytellers can use the following commands to manage the game.

-   **Use a private channel:** Use a private channel to manage the game. This will prevent other users from seeing your commands. To create a private channel, use `/admin settings`
-   **Create Characters**: Use `/storyteller character create` to create an NPC.
-   **Roll Dice:** Use `/storyteller roll_traits` to quickly roll dice for NPCs.

## 7. ROLES IN VALENTINA NOIR

In Valentina Noir, users can have one of three distinct roles, each with its own responsibilities and capabilities. Understanding these roles helps in managing and participating in the game effectively.

### Admin

The Admin is responsible for overall management and configuration of the Valentina Noir system within the Discord server. This role typically includes:

-   **Setting Up**: Configuring the system, managing permissions, and ensuring that everything is running smoothly.
-   **User Management**: Assigning roles to users, such as designating Storytellers or managing player access.
-   **Troubleshooting**: Handling technical issues, updates, and coordinating with the Valentina Noir support if needed.
-   **Managing Settings**: Use `/admin settings` to access various administrative settings.

### Storyteller

The Storyteller is the game master, guiding the narrative and controlling non-player characters (NPCs), events, and the overall direction of the game. Responsibilities include:

-   **Narrative Control**: Creating and managing Chronicles, chapters, NPCs, and notes.
-   **Game Management**: Rolling dice for NPCs, controlling game flow, and ensuring fair play.
-   **Player Interaction**: Engaging with players, managing in-game events, and making judgment calls.
-   **Commands**: Various commands like `/storyteller character create` and `/storyteller roll_traits` are available to manage the game.

### Player

Players are the participants in the game, controlling individual characters and interacting with the story as it unfolds. As a player, you will:

-   **Character Management**: Create, claim, and manage your character, including stats, traits, and abilities.
-   **Gameplay Participation**: Engage in gameplay by rolling dice, using macros, and making decisions for your character.
-   **Collaboration**: Work with other players and the Storyteller to create an engaging and immersive story.
-   **Commands**: Utilize commands like `/character create`, `/roll`, and `/xp` to interact with the game.

## 8. TROUBLESHOOTING & FAQ

This section provides solutions to common problems and answers to frequently asked questions. If you encounter an issue not covered here, please refer to the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina) for support.

**Q: My dice rolls are not working. What's wrong?**
**A:** Verify that you are using the correct syntax for the roll command, such as `/roll traits <stat1> <stat2>`. If the issue continues, try unclaiming and reclaiming your character.

**Q: I found a bug. How do I report it?**
**A:** Please report any bugs or issues on the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina). Provide as much detail as possible to help with troubleshooting.

**Q: I have a feature request. Who do I tell?**
**A:** Please file an issue on the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina). Provide as much detail as possible on the feature you would like to see.

**Q: Can I play multiple characters at once?**
**A:** You can create multiple characters, but you can only claim and play one character at a time.

**Q: How do I become a Storyteller or Admin?**
**A:** Roles like Storyteller and Admin are typically assigned by the server owner or existing Admins. Speak with them if you are interested in taking on one of these roles.

**Q: Can I use Valentina Noir for other role-playing games besides Vampire the Masquerade?**
**A:** Valentina Noir is specifically designed for a highly customized version of Vampire the Masquerade. While some features might be applicable to other games, it may not fully support them.

### Need More Help?

If you have a question or issue not covered here, please consult the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina) or reach out to the community for assistance.
