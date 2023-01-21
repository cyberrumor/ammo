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
    def __init__(self, conf, plugin_file):
        self.conf = conf
        self.plugin_file = plugin_file
        self.mods = []
        self.plugins = []

    def load_mods(self):
        if os.path.isfile(self.conf):
            return load_mods_from(self.conf)
        mods = []
        mod_folders = [i for i in os.listdir(MODS) if os.path.isdir(i)]
        for mod in os.listdir(MODS):
            mods.append(Mod(mod, os.path.join(MODS, mod), False))
        self.mods = mods


    def load_mods_from_conf(self):
        pass


    def load_plugins(self):
        plugins = []
        with open(self.plugin_file, "r") as file:
            for line in file:
                if line.startswith('#'):
                    continue
                if line.startswith('*'):
                    plugins.append(Esp(line.strip('*').strip(), True))
                else:
                    plugins.append(Esp(line.strip(), False))
        self.plugins = plugins
        return True


    def save_plugins(self):
        """
        responsible for writing Plugins.txt
        """
        with open(self.plugins, "w") as file:
            for esp in self.plugins:
                file.write(f"{'*' if esp.enabled else ''}{esp.name}\n")
        return True


    def print_status(self):
        """
        outputs a list of all mods, then a list of all plugins.
        """
        for index, components in enumerate([self.mods, self.plugins]):
            print()
            print(f" ### | Enabled | {'Mod name' if index == 0 else 'Plugin name'}")
            print("-----|---------|-----")
            for priority, component in enumerate(components):
                num = f"[{priority}]     "
                l = len(str(priority)) + 1
                num = num[0:-l]
                enabled = "[True]    " if component.enabled else "[False]   "
                print(f"{num} {enabled} {component.name}")
            print()


    def help(self, *args):
        """
        prints help text.
        """
        print()
        for k, v in {
            "help": "show this help",
            "activate": "activate a component. Usage: activate mod|plugin <index>",
            "deactivate": "deactivate a component. Usage: deactivate mod|plugin <index>",
            "commit": "commit the configuration to disk. Usage: commit",
            "delete": "delete a mod and its plugins. Forces config reload from disk. Usage: delete <index>",
            "move": "move a component from index to index. Usage: move mod|plugin <from_index> <to_index>",
            "exit": "quit oom without applying changes.",
        }.items():
            print(f"{k} - {v}")
        print()
        input("[Enter] to continue")
        return True


    def _set_component_state(self, mod_type, mod_index, state):
        """
        activate or deactivate a component. Returns success.
        """
        index = None
        try:
            index = int(mod_index)
        except ValueError:
            return False

        # validation
        if mod_type not in ["plugin", "mod"]:
            print(f"expected 'plugin' or 'mod', got arg {mod_type}")
            return False
        components = self.plugins.copy() if mod_type == "plugin" else self.mods.copy()
        if index > len(components) - 1:
            return False
        components[index].enabled = state
        return True


    def activate(self, mod_type, mod_index):
        """
        activate a component. Returns success.
        """
        return self._set_component_state(mod_type, mod_index, True)


    def deactivate(self, mod_type, mod_index):
        """
        deactivate a component. Returns success.
        """
        return self._set_component_state(mod_type, mod_index, False)


    def delete(self, mode_index):
        """
        deletes a component from oom's mod dir. Forces data reload from disk,
        possibly discarding unapplied changes.
        """
        return True


    def move(self, mod_type, old_mod_index, new_mod_index):
        """
        move a mod or plugin from old index to new index.
        """
        return True
        

    def commit(self):
        """
        This method is responsible for computing the files to stage,
        writing oom.conf, and writing Plugins.txt.
        """
        return False


    def run(self):
        # complete setup
        self.load_mods()
        self.load_plugins()

        self.command = {
            # cmd: (method, len(args))
            "help": {"func": self.help, "num_args": 0},
            "activate": {"func": self.activate, "num_args": 2},
            "deactivate": {"func": self.deactivate, "num_args": 2},
            "move": {"func": self.move, "num_args": 3},
            "commit": {"func": self.commit, "num_args": 0},
            "delete": {"func": self.delete, "num_args": 1},
            "exit": {"func": exit, "num_args": 0},
        }

        cmd = ""
        while cmd != "exit":
            os.system("clear")
            self.print_status()
            cmd = input(">_: ")
            if not cmd:
                continue
            cmds = cmd.split()
            args = []
            func = cmds[0]
            if len(cmds) > 1:
                args = cmds[1:]
            if func not in self.command:
                self.help()
                continue
            command = self.command[func]
            if command["num_args"] != len(args):
                print(f"{func} expected {command['num_args']} arg(s) but received {len(args)}")
                input("[Enter]")
                continue
            if command["num_args"] == 0:
                ret = command["func"]()
            elif command["num_args"] == 1:
                ret = command["func"](args[0])
            elif command["num_args"] == 2:
                ret = command["func"](args[0], args[1])
            else:
                ret = command["func"](args[0], args[1], args[2])

            if not ret:
                input("[Enter]")
                continue

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

