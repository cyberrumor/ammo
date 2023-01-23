# oom
Obviously Organizes Mods

A Terminal-Based Mod Organizer for Linux

# Features
- Works on Linux (and probably only on Linux).
- Manages mod and plugin load order independently of one another.
- Deletes mods and downloads.
- Installs mods from ~/Downloads folder.
- Manages activation state of mods and plugins.
- Deactivating a mod auto-hides its plugins.
- Handles file conflicts correctly.
- Disable all mods and 'commit' to return to vanilla skyrim.
- Works via symbolic links. No performance impact!

# Planned Features
- Handle mods that are packaged like this: modname/extra_folder/Data
- Handle omod and exe file types during install command.
- Expand to other Bethesda games. Fallout4, Oblivion, etc.
- Handle fomod installers, someday, maybe.
- Handle bain installers, someday, maybe.
- LOOT integration, someday, maybe.

# Dependencies
- Linux version of Steam, Proton.
- Python3
- p7z (and the 7z cli utility somewhere in your PATH, which should
  be automatic if you have p7z installed).

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
- Launch the game through steam. If you want to use skse, copy skse64_loader.exe to SkyrimSELauncher.exe.

# How to Manully Install FOMOD
- Download the mod to your ~/Downloads folder.
- Launch oom and install the mod with `install <download index>`. Close oom.
- check ~/.local/share/oom/Skyrim\ Special\ Edition/mods/your_mod_name
- Inside that dir, create a `Data` folder.
- Move the contents of the folders of your choice inside the new Data folder.
- Delete all the folders besides the Data folder.
- Launch oom, activate the mod and commit.

# Disclaimer
- I waive all liability. Use at your own risk.


