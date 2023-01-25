# ammo
Almost Manual Mod Organizer

A Simple Terminal-Based Mod Organizer for Linux

# Supported Games
- Skyrim
- Skyrim SE
- Oblivion
- Fallout 4

# Features
- Handles file conflicts correctly.
- Deactivating a mod auto-hides its plugins.
- Ability to manage load order of mods and plugins.
- Ability to install mods from ~/Downloads folder.
- Ability to delete downloads and installed mods.
- Ability to return to vanilla game state easily.

# Limitations
- No fomod installer.
- No dependency checking.
- No automated load order handling.
- No external tool integration.
- Manual downloads only.

# Planned Features
- New name.
- Ability to rename mods and downloads.
- Morrowind support.
- Automated testing.
- FOMOD installer.
- Launcher for .exe files anywhere inside the game folder.
- Select multiple files at once for activation, deactivation, or deletion.

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

```
activate   activate mod|plugin <index>               add a mod or plugin to the stage.
commit     commit                                    make this configuration persistent.
deactivate deactivate mod|plugin <index>             remove component from the stage.
delete     delete download|mod <index>               delete a mod or download from the filesystem.
disable    disable mod|plugin <index>                alias for deactivate.
enable     enable mod|plugin <index>                 alias for activate.
exit       exit                                      quit without saving changes.
help       help                                      show this menu.
install    install <index>                           extract a mod from downloads.
move       move mod|plugin <from_index> <to_index>   rearrange the load order.
refresh    refresh                                   reload all mods/plugins/downloads/orders from disk.
vanilla    vanilla                                   disable all non-vanilla components and clean up.
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
- This will rename your downloads to not have ****** up names.
- This will remove symlinks and empty directories from your game dir.

