# oom
Organizes Obvious Mods

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
git clone https://github.com/cyberrumor/oom
cd oom
echo "$PWD/oom/oom.py" >> bin/oom
sudo cp bin/oom /usr/local/bin
```

# Usage Instructions
- Activate a component by type and index: `activate mod 0` or `activate plugin 5`.
- Deactivate a component by type and index: `deactivate mod 0` or `deactivate plugin 2`.
- Arrange your load order with the move command: `move mod 0 3`.
  This will cause the mod at index 0 to be inserted at index 3. Mods that had indicies 3 or lower
  will be moved up.
- Make changes persist on disk! Nothing will be changed if you don't commit: `commit`
- Use the `help` command so you don't have to read instructions from here :)

# Usage with non-obvious mods like FOMODs
- Download the mod to your ~/Downloads folder.
- Launch oom and install the mod with `install <download index>`. Close oom.
- check ~/.local/share/oom/your_game_name/mods/your_mod_name
- Inside that dir, create a `Data` folder.
- Move the contents of the folders of your choice inside the new Data folder.
- Delete all the folders besides the Data folder.
- Launch oom, activate the mod and commit.

# Disclaimer
- I waive all liability. Use at your own risk.
- This will rename your downloads to not have ****** up names.
- This will remove symlinks and empty directories from your game dir.

