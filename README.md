# AMMO

Almost Manual Mod Organizer

A Simple Terminal-Based Mod Organizer for Linux

## Supported Games

- Starfield
- Skyrim
- Skyrim SE
- Oblivion
- Fallout 4
- Fallout New Vegas
- Enderal
- Enderal Special Edition

## Features

- install mods from ~/Downloads
- activate/deactivate mods/plugins
- reorder mods/plugins
- rename mods/downloads
- delete mods/plugins/downloads
- autosort plugins by mod order
- supports FOMOD configuration

## Dependencies

- Python 3.11 or later
- Steam from [Flatpak](https://flathub.org/apps/com.valvesoftware.Steam) or official repos.
- [p7z](https://github.com/p7zip-project/p7zip) from official repos.
- [pipx](https://github.com/pypa/pipx) from official repos.

## Installation

```
git clone https://github.com/cyberrumor/ammo
cd ammo
pipx install . --force
```

## Usage

`ammo` - Launch the interactive shell. Select a game via index if prompted.
```
activate_mod      : <index>             : Enabled mods will be loaded by game.
                  :                     : - `activate_mod 0`
                  :                     : - `activate_mod all`
................................................................................................
activate_plugin   : <index>             : Enabled plugins will be loaded by the game.
                  :                     : - `activate_plugin 0`
                  :                     : - `activate_plugin all`
................................................................................................
collisions        : <index>             : Show file conflicts for a mod. Mods prefixed with
                  :                     : asterisks have file conflicts. Mods prefixed with x
                  :                     : install no files.
                  :                     : - `collisions 0`
................................................................................................
commit            :                     : Apply pending changes.
................................................................................................
configure         : <index>             : Configure a fomod.
                  :                     : - `configure 0`
................................................................................................
deactivate_mod    : <index>             : Diabled mods will not be loaded by game.
                  :                     : - `deactivate_mod 0`
                  :                     : - `deactivate_mod all`
................................................................................................
deactivate_plugin : <index>             : Disabled plugins will not be loaded by game.
                  :                     : - `deactivate_plugin 0`
                  :                     : - `deactivate_plugin all`
................................................................................................
delete_download   : <index>             : Removes specified download from the filesystem.
                  :                     : - `delete_download 0`
                  :                     : - `delete_download all`
................................................................................................
delete_mod        : <index>             : Removes specified mod from the filesystem.
                  :                     : - `delete_mod 0`
                  :                     : - `delete_mod all`
................................................................................................
delete_plugin     : <index>             : Removes specified plugin from the filesystem.
                  :                     : - `delete_plugin 0`
                  :                     : - `delete_plugin all`
................................................................................................
exit              :                     : Quit.
................................................................................................
find              : [<keyword> ... ]    : Show only components with any keyword. Execute without
                  :                     : args to show all.
                  :                     : - `find`
                  :                     : - `find keyword1`
                  :                     : - `find keyword1 keyword2`
................................................................................................
help              :                     : Show this menu.
................................................................................................
install           : <index>             : Extract and manage an archive from ~/Downloads.
                  :                     : - `install 0`
                  :                     : - `install all`
................................................................................................
log               :                     : Show debug log history.
................................................................................................
move_mod          : <index> <new_index> : Larger numbers win file conflicts.
                  :                     : - `move_mod 0 1`
................................................................................................
move_plugin       : <index> <new_index> : Larger numbers win file conflicts.
                  :                     : - `move_plugin 0 1`
................................................................................................
refresh           :                     : Abandon pending changes.
................................................................................................
rename_download   : <index> <name>      : Names may contain alphanumerics and underscores.
                  :                     : - `rename_download 0 some_text`
................................................................................................
rename_mod        : <index> <name>      : Names may contain alphanumerics and underscores.
                  :                     : - `rename_mod 0 some_text`
................................................................................................
sort              :                     : Arrange plugins by mod order.
................................................................................................
tools             :                     : Manage tools.
................................................................................................
```


## License

GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.
