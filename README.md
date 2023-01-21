# oom
Obviously Organizes Mods

# Goals
- Made primarily for Linux
- Works with Skyrim SE
- Easy to use
- Interactive CLI

# Dependencies
- Linux version of Steam with proton enabled

# Build instructions
```
git clone https://github.com/cyberrumor/oom
cd oom
cargo build --release
```

# Installation Instructions
```
TODO: installation instructions
```

# Usage Instructions
- launch from cli with `oom`.
- point oom to your Skyrim installation directory (the folder with the executable).
- point oom to your wine prefix. By default, `$HOME/.steam/steam/steamapps/compatdata/489430/pfx`.
- `XDG_CONFIG_HOME/oom/oom.conf` || `$HOME/.config/oom/oom.conf` oom's config file.
- `XDG_DATA_HOME/oom` || `$HOME/.local/share/oom` stores downloaded mods.


# Implementation Details
- Activating a mod will add its files to the stage.
- Conflicting files replace staged files.
- The commit command will create symlinks for staged files in your Skyrim/Data dir.
- The commit command will also modify Plugins.txt as necessary.
- The commit command will modify oom.conf for persistent config data.
- Launch the game through Steam. oom does not have to be running.

