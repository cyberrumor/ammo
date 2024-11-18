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
................................................................................................
activate   : (mod|plugin) <index>             : Enabled components will be loaded by game.
           :                                  : - `activate mod 1`
           :                                  : - `activate mod all`
           :                                  : - `activate plugin 1`
           :                                  : - `activate plugin all`
................................................................................................
collisions : <index>                          : Show file conflicts for a mod. Mods prefixed
           :                                  : with asterisks have file conflicts. Mods
           :                                  : prefixed with x install no files.
           :                                  : - `collisions 0`
................................................................................................
commit     :                                  : Apply pending changes.
................................................................................................
configure  : <index>                          : Configure a fomod.
           :                                  : - `configure 0`
................................................................................................
deactivate : (mod|plugin) <index>             : Disabled components will not be loaded by game.
           :                                  : - `deactivate mod 1`
           :                                  : - `deactivate mod all`
           :                                  : - `deactivate plugin 1`
           :                                  : - `deactivate plugin all`
................................................................................................
delete     : (mod|download|plugin) <index>    : Removes specified file from the filesystem.
           :                                  : - `delete download 1`
           :                                  : - `delete download all`
           :                                  : - `delete mod 1`
           :                                  : - `delete mod all`
           :                                  : - `delete plugin 1`
           :                                  : - `delete plugin all`
................................................................................................
exit       :                                  : Quit.
................................................................................................
find       : [<keyword> ... ]                 : Show only components with any keyword. Execute
           :                                  : without args to show all.
           :                                  : - `find`
           :                                  : - `find keyword1`
           :                                  : - `find keyword1 keyword2`
................................................................................................
help       :                                  : Show this menu.
................................................................................................
install    : <index>                          : Extract and manage an archive from ~/Downloads.
           :                                  : - `install 0`
           :                                  : - `install all`
................................................................................................
log        :                                  : Show debug log history.
................................................................................................
move       : (mod|plugin) <index> <new_index> : Larger numbers win file conflicts.
           :                                  : - `move mod 1 2`
           :                                  : - `move plugin 1 2`
................................................................................................
refresh    :                                  : Abandon pending changes.
................................................................................................
rename     : (mod|download) <index> <name>    : Names may contain alphanumerics and underscores.
           :                                  : - `rename download 1 some_text`
           :                                  : - `rename mod 1 some_text`
................................................................................................
sort       :                                  : Arrange plugins by mod order.
................................................................................................
tools      :                                  : Manage tools.
................................................................................................
```


## License

GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.
