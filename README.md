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
- Fuzzy "find" command easily displays relevant resources.

# Limitations
- No dependency checking or automated load order handling.
- Manual downloads only.
- FOMOD install wizard is in beta. Please report any bugs you encounter.
- If the FOMOD needs to put things _above_ the game's Data dir, the FOMOD will require
  manual configuration.

# Dependencies
- Linux version of Steam, Proton.
- Python3
- p7z (or something else that puts 7z in your PATH).

# Installation Instructions
```
cd /path/to/desired/install/location
git clone https://github.com/cyberrumor/ammo
cd ammo
echo "$PWD/ammo/ammo.py" >> bin/ammo
sudo cp bin/ammo /usr/local/bin
```

# Updating Instructions
```
cd /path/to/ammo/installation/directory
git pull
```
If you have mods that were previously misbehaving and are wondering whether you need to
reinstall them to benefit from the update, you don't. However, patch notes will specify
whether re-running a fomod install wizard could resolve issues. If this is the case,
you may want to run `configure <index>` on misbehaving fomods.

# Usage Instructions

`ammo` - Launch the interactive shell. Select a game via index if prompted.

At any time from the interactive shell, you can type `help` to show this menu:

```
activate   mod|plugin <index>                 Enabled components will be loaded by game.
commit                                        Apply and save this configuration.
configure  <index>                            Configure a fomod.
deactivate mod|plugin <index>                 Disabled components will not be loaded by game.
delete     mod|download <index>               Removes specified file from the filesystem.
exit                                          Quit. Prompts if there are changes.
find       [<keyword> ...]                    Show only components with any keyword. `find` without args resets.
help                                          Show this menu.
install    <index>                            Extract and manage an archive from ~/Downloads.
move       mod|plugin <from_index> <to_index> Larger numbers win file conflicts.
refresh                                       Reload configuration and files from disk.
vanilla                                       Disable all managed components and clean up.
```

# Disclaimer
- I waive all liability. Use at your own risk.
- When you install a file from ~/Downloads, the filename may be sanitized.
- This will remove symlinks and empty directories from your game dir.

