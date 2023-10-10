# AMMO
Almost Manual Mod Organizer

A Simple Terminal-Based Mod Organizer for Linux

# Supported Games
- Starfield
- Skyrim
- Skyrim SE
- Oblivion
- Fallout 4
- Enderal
- Enderal Special Edition

# AMMO vs Manual
- AMMO only:
  - FOMOD install wizard.
  - Ability to return to vanilla game state easily.
  - Load order management, including activation / deactivation.
- AMMO and Manual:
  - No dependency checking or automated load order handling.
  - No Nexus integration. Manual downloads only.
- Manual only:
  - Even minor mistakes are catastrophic.
  - Returning to vanilla requires nuke/pave/reinstall.

# Dependencies
- Linux version of Steam, Proton.
- Python3
- p7z (or something else that puts 7z in your PATH).

# Installation Instructions
Steam Deck users:
```
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

Everyone:
```
echo 'PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
PATH="$HOME/.local/bin:$PATH"
git clone https://github.com/cyberrumor/ammo
cd ammo
pip3 install -r requirements.txt || pip3 install --break-system-packages -r requirements.txt
pip3 install . || pip3 install --break-system-packages .
```
You can now execute ammo with the terminal command `ammo`.

# Updating Instructions
```
cd /path/to/ammo/clone/dir
git pull
pip3 install --force-reinstall . || pip3 install --break-system-packages --force-reinstall .
```

# Usage Instructions

`ammo` - Launch the interactive shell. Select a game via index if prompted.

```
activate   mod|plugin <index>                 Enabled components will be loaded by game.
commit                                        Apply pending changes.
configure  <index>                            Configure a fomod.
deactivate mod|plugin <index>                 Disabled components will not be loaded by game.
delete     mod|download <index>               Removes specified file from the filesystem.
exit                                          Quit. Prompts if there are changes.
find       [<keyword> ...]                    Show only components with any keyword. `find` without args resets.
help                                          Show this menu.
install    <index>                            Extract and manage an archive from ~/Downloads.
move       mod|plugin <from_index> <to_index> Larger numbers win file conflicts.
refresh                                       Abandon pending changes.
vanilla                                       Disable all managed components and clean up.
```

# Technical Details
- AMMO works via creating hardlinks (or symlinks with `ammo -s`) in your game directory
  pointing to your mod files.
- When you install an archive, the archive may be renamed to remove special characters.
- This will remove symlinks, hardlinks, and empty directories from your game dir,
  and reinstall them whenever you commit.

# License
GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.

