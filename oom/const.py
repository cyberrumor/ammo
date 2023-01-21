#!/usr/bin/env python3
import os

APP_ID = "489830"
APP_NAME = "Skyrim Special Edition"
HOME = os.environ["HOME"]
STEAM = os.path.join(HOME, ".local/share/Steam/steamapps")
PFX = os.path.join(STEAM, f"compatdata/{APP_ID}/pfx/")
GAME_DIR = os.path.join(STEAM, f"common/{APP_NAME}")
PLUGINS = os.path.join(STEAM, f"{PFX}/drive_c/users/steamuser/AppData/Local/{APP_NAME}/Plugins.txt")
DATA = os.path.join(GAME_DIR, "Data")
MODS = os.path.join(HOME, ".local/share/oom/mods")
CONF_DIR = os.path.join(HOME, ".config/oom/")

if __name__ == "__main__":
    print("this file just serves to load constants into various modules,")
    print("and does nothing on its own.")
