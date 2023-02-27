# AMMO
Almost Manual Mod Organizer

A Simple Terminal-Based Mod Organizer for Linux

# Supported Games
- Skyrim
- Skyrim SE
- Oblivion
- Fallout 4
- Enderal
- Enderal Special Edition

# Features
- Handles file conflicts correctly.
- Deactivating a mod auto-hides its plugins.
- Ability to manage load order of mods and plugins.
- Ability to install mod archives from ~/Downloads folder.
- Ability to delete downloads and installed mods.
- Ability to return to vanilla game state easily.
- FOMOD install wizard.
- Can install mods that other mod organizers can not, for example:
  - SKSE
  - Both parts of SSE Engine Fixes

# Limitations
- No dependency checking or automated load order handling.
- Manual downloads only.
- FOMOD install wizard is considered "beta", there are likely bugs that need to be ironed out.

# Planned Features
- Morrowind support.
- More robust FOMOD install wizard.

# Dependencies
- Linux version of Steam, Proton.
- Python3
- p7z (or something else that puts 7z in your PATH).

# Installation Instructions
```
git clone https://github.com/cyberrumor/ammo
cd ammo
echo "$PWD/ammo/ammo.py" >> bin/ammo
sudo cp bin/ammo /usr/local/bin
```

# Usage Instructions

`ammo` - Launch the interactive shell. Select a game via index if prompted.

At any time from the interactive shell, you can type `help` to show this menu:

```
activate   mod|plugin <index>                 Enabled components will be loaded by game.
commit                                        Apply and save this configuration.
deactivate mod|plugin <index>                 Disabled components will not be loaded by game.
delete     mod|download <index>               Removes specified file from the filesystem.
exit                                          Quit. Prompts if there are changes.
help                                          Show this menu.
install    <index>                            Extract and manage an archive from ~/Downloads.
move       mod|plugin <from_index> <to_index> Larger numbers win file conflicts.
refresh                                       Reload configuration and files from disk.
vanilla                                       Disable all managed components and clean up.
```

# Usage with non-obvious mods like FOMODs
- Download the mod to your ~/Downloads folder.
- Launch ammo and install the mod with `install <download index>`. Close ammo.
- check ~/.local/share/ammo/your_game_name/mods/your_mod_name
- Inside that dir, create a `Data` folder.
- Move the contents of the folders of your choice inside the new Data folder.
- Delete all the folders besides the Data folder.
- Launch ammo, activate the mod and commit.

# Disclaimer
- I waive all liability. Use at your own risk.
- When you install a file from ~/Downloads, the filename may be sanitized.
- This will remove symlinks and empty directories from your game dir.

