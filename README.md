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

## Usage Instructions

`ammo` - Launch the interactive shell. Select a game via index if prompted.

| Command     | Arguments                               | Description |
|-|-|-|
| activate    | (mod\|plugin) \<index>                  | Enabled components will be loaded by game. |
| collisions  | \<index>                                | Show file conflicts for a mod. |
| commit      |                                         | Apply pending changes. |
| configure   | \<index>                                | Configure a fomod. |
| deactivate  | (mod\|plugin) \<index>                  | Disabled components will not be loaded by game. |
| delete      | (mod\|download\|plugin) \<index>        | Removes specified file from the filesystem. |
| exit        |                                         | Quit. |
| find        | [\<keyword> ...]                        | Show only components with any keyword. Execute without args to show all. |
| help        |                                         | Show this menu. |
| install     | \<index>                                | Extract and manage an archive from ~/Downloads. |
| move        | (mod\|plugin) \<from_index> \<to_index> | Larger numbers win file conflicts. |
| refresh     |                                         | Abandon pending changes. |
| rename      | (mod\|download) \<index> \<name>        | Names may contain alphanumerics and underscores. |
| sort        |                                         | Arrange plugins by mod order. |


## License

GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.
