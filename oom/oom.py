#!/usr/bin/env python3
import sys
import os
from mod import Mod, Esp

APP_ID = "489830"
APP_NAME = "Skyrim Special Edition"
HOME = os.environ["HOME"]
STEAM = os.path.join(HOME, ".local/share/Steam/steamapps")
PFX = os.path.join(STEAM, f"compatdata/{APP_ID}/pfx/")
GAME_DIR = os.path.join(STEAM, f"common/{APP_NAME}")
PLUGINS = os.path.join(STEAM, f"{PFX}/drive_c/users/steamuser/AppData/Local/{APP_NAME}/Plugins.txt")
DATA = os.path.join(GAME_DIR, "Data")
MODS = os.path.join(HOME, ".local/share/oom/mods")
DOWNLOADS = os.path.join(HOME, ".local/share/oom/downloads")
CONF_DIR = os.path.join(HOME, ".config/oom/")


class Oom:
    def __init__(self, conf, plugins):
        self.conf = conf
        self.plugins = plugins
        self.mods = []
        self.esps = []


    def load_mods(self):
        if os.path.isfile(self.conf):
            return load_mods_from(self.conf)
        mods = []
        mod_folders = [i for i in os.listdir(MODS) if os.path.isdir(i)]
        for mod in os.listdir(MODS):
            mods.append(Mod(mod, os.path.join(MODS, mod), False))
        self.mods = mods


    def load_mods_from(self, conf):
        pass


    def load_esps(self):
        esps = []
        with open(self.plugins, "r") as file:
            for line in file:
                if line.startswith('#'):
                    continue
                if line.startswith('*'):
                    esps.append(Esp(line.strip('*').strip(), True))
                else:
                    esps.append(Esp(line.strip(), False))
        self.esps = esps


    def print_status(self):
        for components in [self.mods, self.esps]:
            print()
            print(" ### | Enabled | Name")
            print("-----|---------|-----")
            for priority, component in enumerate(components):
                num = f"[{priority}]     "
                l = len(str(priority)) + 1
                num = num[0:-l]
                enabled = "[True]    " if component.enabled else "[False]   "
                print(f"{num} {enabled} {component.name}")
            print()


    def run(self):
        # complete setup
        self.load_mods()
        self.load_esps()

        cmd = ""
        while cmd != "exit":
            os.system("clear")
            self.print_status()
            cmd = input(">_: ")


if __name__ == "__main__":

    # Create expected directories if they don't alrady exist.
    expected_dirs = [MODS, DOWNLOADS, CONF_DIR]
    for directory in expected_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # This is where our config will live.
    oom_conf = os.path.join(CONF_DIR, "oom.conf")

    # Create an instance of Oom and run it.
    oom = Oom(oom_conf, PLUGINS)
    exit(oom.run())

