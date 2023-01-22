# oom
Obviously Organizes Mods

# Goals
- Made for Linux
- Works with Skyrim SE
- Easy to use
- Interactive CLI

# TODO
- Extract files from ~/Downloads to oom's mod dir
- Enable the `delete` command.
- More robust handling of mods that are packaged wierd.
- handle FOMOD installers?
- handle BAIN installers?
- logging
- Get a list of game names and steam APP IDs
- Enable use on multiple games

# Dependencies
- Linux version of Steam with proton enabled
- Python3


```
 ### | Activated | Mod name
-----|-----------|-----
[0]    [False]     ussep
[1]    [True]      standard_lighting_templates
[2]    [True]      polishwithoil


 ### | Activated | Plugin name
-----|-----------|-----
[0]    [True]      StandardLightingTemplates.esp
[1]    [True]      PolishWithOil.esp

>_: activate mod 0
```


# Build instructions
```
git clone https://github.com/cyberrumor/oom
cd oom
echo "$PWD/oom/oom.py" >> bin/oom
```

# Installation Instructions
```
sudo cp bin/oom /usr/local/bin
```

# Setup Instructions
- Have a vanalla skyrim install. skse should theoretically be fine. Plugins.txt should be empty.
- oom expects mods to be in ~/.local/share/oom/mods
- oom can handle the following styles of packaging right now:
  - modname/Data/some_plugin.esp
  - modname/some_plugin.esp
- oom can't handle this kind of thing yet:
  - modname/4.5.1/Data/some_plugin.esp
  - modname/4.5.1/some_plugin.esp

# Usage Instructions
- Activate a component by type and index: `activate mod 0` or `activate plugin 5`.
- Deactivate a component by type and index: `deactivate mod 0` or `deactivate plugin 2`.
- Arrange your load order with the move command: `move mod 0 3`.
  This will cause the mod at index 0 to be inserted at index 3. Mods that had indicies 3 or lower
  will be moved up.
- Make changes persist on disk! Nothing will be changed if you don't commit: `commit`
- Use the `help` command so you don't have to read instructions from here :)


# Implementation Details of `commit`
- unlink all symlinks and delete all empty directories in Skyrim/Data.
- Iterates through enabled mods.
- Mods have a list of full file paths associated with them.
- A "staging" dictionary is populated with these paths, and the path that the mod's files will go.
- Since we are iterating in order of your load order, this resolves conflicts automatically.
- Mods with larger number indices will win conflicts.
- We iterate through our staging dictionary and create symlinks with their values.

# Disclaimer
- This is barely tested.
- I've only tested with small load orders (3 or 4 mods).
- This only works on mods pacakged with 'Data' as their parent dir name.
- Error handling is not very robust.
- This will delete symlinks in your Skyrim Data dir.
- I waive all liability. Use at your own risk.


