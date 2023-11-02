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
find       [<keyword> ...]                    Fuzzy filter. `find` without args removes filter.
help                                          Show this menu.
install    <index>                            Extract and manage an archive from ~/Downloads.
move       mod|plugin <from_index> <to_index> Larger numbers win file conflicts.
refresh                                       Abandon pending changes.
```

# Tips and Tricks

- Note that the `de/activate mod|plugin` command supports `all` in place of `<index>`.
  This will activate or deactivate all mods or plugins that are visible. Combine this
  with the `find` command to quickly organize groups of components with related names.
  You can leverage this to automatically sort your plugins to the same order as your
  mod list:
  ```
  deactivate mod all
  # sort your mods with the move command
  activate mod all
  activate plugin all
  commit
  ```
- The `find` command accepts a special `fomods` argument that will filter by fomods.

- The `find` command allows you to locate plugins owned by a particular mod, or mods
  that have a particular plugin. It also lets you find mods / plugins / downloads via
  keyword. This is an additive filter, so more words equals more matches.

- You can easily return to vanilla like this:
  ```
  deactivate mod all
  commit
  ```

- If you don't know how many components are in your list and you want to move a
  component to the bottom, you can throw in an arbitrarily large number as the
  `<to index>` for the `move` command, and it will be moved to the last position.
  This only works for the `move` command.

- If you have several downloads and you want to install all of them at once, simply
  `install all`.

- Combining `find` filters with `all` is a great way to quickly manage groups of
  related components, as the `all` keyword only operates on visible components.

# Contributing

- Fork the repository, make changes on your fork, then open a PR.
- Format patches with ruff or black.

# AMMO is Simple

Please observe the following criteria when considering whether
a change would be acceptable:

- Python only.
- Standard lib imports only.
- Unix filesystems only.
- Single threaded.
- Offline.
- Databaseless.
- Daemonless.
- Testable without the UI.
- Installs mod files via symlink.
- UI is terminal based only.
- AMMO is not:
  - a download manager.
  - an API client.
  - a program launcher.

# Why Symlinks?

- The configured state is discovered via file inspection and logic. This avoids
  entire classes of bugs that organizers relying on databases must contend with.
- Vast reduction in code and test complexity.
- It's easy to identify which mod provides a particular file.
- We can return to vanilla game state by simply unlinking all symlinks then
  removing empty folders. This actually occurs every time you commit, which
  provides a plethora of benefits also.
- They consume an insignificant amount of storage.

# Code Organization

- UI is responsible for mapping user input to methods of a controller, ensuring
  user input is converted to the argument types that those methods expect,
  displaying errors, and drawing to the screen.
- ModController exposes an interface to install, delete, activate, deactivate,
  and reorder mods. Committing changes builds a conflict-resolved hashmap
  of all mod file's sources and their intended destinations, then creates symlinks.
  ModController can 'configure' a fomod, which instantiates a FomodController and
  runs a nested UI with it.
- FomodController exposes an interface to switch pages and selections of a fomod's
  configurable options. When you advance past the last page, the selected files
  are put in a conflict-resolved hashmap hashmap and _copied_ to a Data folder
  local to that fomod. At this point, the FomodController's UI will break from
  the read/exec/print loop and execution will pick back up from the end of
  ModController.configure.

# License
GNU General Public License v2, with the exception of some of the mock mods used for testing,
which are subject to their packaged license (if it exists), which also contains credits.

