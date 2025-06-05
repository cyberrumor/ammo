# Almost Manual Mod Organizer (ammo)

Say "No!" to _annoying bullshit_, like:

- Advertisements.
- Auto-updates.
- Overreaching integrations (screenshots, saves, socials, tracking of tax
  deductions earned through donations).
- Account-required-before-use fuckery.
- Uncensored BDSM hentai in the in-app news feed even though you've turned off
  adult content twice.
- GUIs (and other bloat).

Ammo is _purely_ a mod manager. This means it is concerned with exactly _one_
problem, and it solves it really fucking well:

> **As a Linux gamer**,
>
> **I want** easy, safe, and transparent mod management,
>
> **so that** I never have to reinstall the game or verify files, and can audit
> how mods are installed.

Ammo's interface is an interactive shell designed to make you feel 27% cooler
while modding (especially when you're installing the sword that one-shots God).
Under the hood, it hooks mods up to a game by adding symlinks to the game
directory which point at mod files.

Ammo is forever free from _annoying bullshit_ (a decision by yours truly that
required a whopping 100 IQ).

## Supported Games

- Enderal
- Enderal Special Edition
- Fallout 4
- Fallout New Vegas
- Oblivion
- Oblivion Remastered
- Sims 4
- Skyrim
- Skyrim Special Edition
- Skyrim VR
- Starfield

## Features

- install mods from ~/Downloads
- activate/deactivate mods/plugins
- reorder mods/plugins
- rename mods/downloads
- delete mods/plugins/downloads
- autosort plugins by mod order
- supports FOMOD configuration
- file conflict detection

## Dependencies

- Python 3.12 or later
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

```
usage: ammo [-h] [--downloads PATH] [--conf PATH] [--mods PATH] [--tools PATH] [--title TITLE]

Almost Manual Mod Organizer

options:
  -h, --help        show this help message and exit
  --downloads PATH  directory containing installable archives
  --conf PATH       directory containing configs for managed games
  --mods PATH       directory containing mods for this session
  --tools PATH      directory containing tools for this session
  --title TITLE     manage a detected game with TITLE (skip game selection menu)
```

## Help

```
............................................................................................
activate   : (mod|plugin) <index>             : Enabled components will be loaded by the
           :                                  : game.
           :                                  : - `activate mod 1`
           :                                  : - `activate mod all`
           :                                  : - `activate plugin 1`
           :                                  : - `activate plugin all`
............................................................................................
collisions : <index>                          : Show file conflicts for a mod. Mods prefixed
           :                                  : with asterisks have file conflicts. Mods
           :                                  : prefixed with x install no files.
           :                                  : - `collisions 0`
............................................................................................
commit     :                                  : Apply pending changes.
............................................................................................
configure  : <index>                          : Configure a fomod.
           :                                  : - `configure 0`
............................................................................................
deactivate : (mod|plugin) <index>             : Disabled components will not be loaded by
           :                                  : the game.
           :                                  : - `deactivate mod 1`
           :                                  : - `deactivate mod all`
           :                                  : - `deactivate plugin 1`
           :                                  : - `deactivate plugin all`
............................................................................................
delete     : (mod|plugin|download) <index>    : Removes the specified file from the
           :                                  : filesystem.
           :                                  : - `delete download 1`
           :                                  : - `delete download all`
           :                                  : - `delete mod 1`
           :                                  : - `delete mod all`
           :                                  : - `delete plugin 1`
           :                                  : - `delete plugin all`
............................................................................................
exit       :                                  : Quit.
............................................................................................
find       : [<keyword> ... ]                 : Show only components with any keyword.
           :                                  : Execute without args to show all.
           :                                  : - `find`
           :                                  : - `find keyword1`
           :                                  : - `find keyword1 keyword2`
............................................................................................
help       :                                  : Show this menu.
............................................................................................
install    : <index>                          : Extract and manage an archive from
           :                                  : ~/Downloads.
           :                                  : - `install 0`
           :                                  : - `install all`
............................................................................................
log        :                                  : Show debug log history.
............................................................................................
move       : (mod|plugin) <index> <new_index> : Larger numbers win conflicts.
           :                                  : - `move mod 1 2`
           :                                  : - `move plugin 1 2`
............................................................................................
refresh    :                                  : Abandon pending changes.
............................................................................................
rename     : (mod|download) <index> <name>    : Names may contain alphanumerics, periods,
           :                                  : and underscores.
           :                                  : - `rename download 1 some_text`
           :                                  : - `rename mod 1 some_text`
............................................................................................
sort       :                                  : Arrange plugins by mod order.
............................................................................................
tools      :                                  : Manage tools.
............................................................................................
```

## License

GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.
