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

- Supports Steam from your official repository
- Supports com.valvesoftware.Steam from Flatpak
- Python 3.11 or later
- p7z (or something else that puts 7z in your PATH).

## Installation Instructions

Steam Deck users:

```sh
python -m ensurepip --user --break-system-packages --upgrade
python -m pip install --user --break-system-packages --upgrade pip
```

Everyone:

```sh
echo 'PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
PATH="$PATH:$HOME/.local/bin"
git clone https://github.com/cyberrumor/ammo
cd ammo
pip3 install --user --break-system-packages -r requirements.txt
pip3 install --user --break-system-packages .
```

You can now execute ammo with the terminal command `ammo`.

## Updating Instructions

Check the releases page for possible manual migration steps.
Releases are only published on breaking changes, and are there
for the benefit of people who don't have time to address those
changes. In general, you should be using the most recent
version of the main branch.

```sh
cd /path/to/ammo/clone/dir
git pull
pip3 install --user --break-system-packages --force-reinstall .
```

## Usage Instructions

`ammo` - Launch the interactive shell. Select a game via index if prompted.

| Command     | Arguments                               | Description |
|-|-|-|
| activate    | (mod\|plugin) \<index>                  | Enabled components will be loaded by game |
| collisions  | \<index>                                | Show file conflicts for a mod |
| commit      |                                         | Apply pending changes |
| configure   | \<index>                                | Configure a fomod |
| deactivate  | (mod\|plugin) \<index>                  | Disabled components will not be loaded by game |
| delete      | (mod\|download\|plugin) \<index>        | Removes specified file from the filesystem |
| exit        |                                         | Quit |
| find        | [\<keyword> ...]                        | Show only components with any keyword |
| help        |                                         | Show this menu |
| install     | \<index>                                | Extract and manage an archive from ~/Downloads |
| move        | (mod\|plugin) \<from_index> \<to_index> | Larger numbers win file conflicts |
| refresh     |                                         | Abandon pending changes |
| rename      | (mod\|download) \<index> \<name>        | Names may contain alphanumerics and underscores |
| sort        |                                         | Arrange plugins by mod order |


### Usage Tips and Tricks

- Note that the `{de}activate (mod|plugin)` command supports `all` in place of `<index>`.
  This will activate or deactivate all mods or plugins that are visible. Combine this
  with the `find` command to quickly organize groups of components with related names.

- The `find` command accepts a special `fomods` argument that will filter by fomods.

- The `find` command allows you to locate plugins owned by a particular mod, or mods
  that have a particular plugin. It also lets you find mods / plugins / downloads via
  keyword. This is an additive filter, so more words equals more matches.

- You can easily return to vanilla like this:
  ```sh
  deactivate mod all
  commit
  ```

- If you don't know how many components are in your list and you want to move a
  component to the bottom, you can throw in an arbitrarily large number as the
  `<to index>` for the `move` command, and it will be moved to the last position.
  This only works for the `move` command.

- If you have several downloads and you want to install all of them at once, simply
  `install all`.


## Contributing

If you would like to contribute, please fork the repository, make changes on your fork, then open a PR. Below are some key guidelines to follow for code contributions, but keep in mind the intended scope of AMMO; it is NOT a download manager or API client and it does NOT launch programs.

- Format patches with ruff or black.
- Python only.
- Standard lib imports only.
- Unix filesystems only.
- Single threaded.
- Offline.
- No databases.
- No deamons.
- Testable without the UI.
- Installs mod files via symlink.
- UI is terminal based only.

### Tips and tricks for contributors

You can run tests from the base directory of the repo with `pytest test`.

It may be useful in your iterations to automate UI input before you've written
tests. I find the easiest way to do this is with this sort of strategy:

```sh
(echo "command1 arg1"; echo "command2 arg1") | ammo
```

If you need to recreate a complex set of initial steps then supply manual input,
you can use input redirection:

```sh
(echo "instruction1"; echo "instruction2"; cat <&0) | ammo
```

## Technical Details

AMMO works via creating symlinks in your game directory pointing to your mod files.

### Why Symlinks?

- The configured state is discovered via file inspection and logic. This avoids
  entire classes of bugs that organizers relying on databases must contend with.
- Vast reduction in code and test complexity.
- It's easy to identify which mod provides a particular file.
- We can return to vanilla game state by simply unlinking all symlinks then
  removing empty folders. This actually occurs every time you commit, which
  provides a plethora of benefits also.
- They consume an insignificant amount of storage.
- They make it possible to use external tools that rely on mod data without
  coupling ammo to those tools.

## License

GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.
