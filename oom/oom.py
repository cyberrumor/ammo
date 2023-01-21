#!/usr/bin/env python3
import sys
import os
from const import *
from mod import Mod, Plugin

class Oom:
    def __init__(self, conf, plugin_file):
        self.conf = conf
        self.plugin_file = plugin_file
        self.mods = []
        self.plugins = []

    def load_mods(self):
        """
        Instance a  Mod class for each mod folder in oom's mod directory.
        """
        if os.path.isfile(self.conf):
            return load_mods_from(self.conf)
        mods = []
        mod_folders = [i for i in os.listdir(MODS) if os.path.isdir(os.path.join(MODS, i))]
        for mod_folder in mod_folders:
            mod = Mod(mod_folder, os.path.join(MODS, mod_folder), False)
            mods.append(mod)
        self.mods = mods


    def load_mods_from_conf(self):
        pass


    def load_plugins(self):
        with open(self.plugin_file, "r") as file:
            for line in file:
                if line.startswith('#'):
                    continue

                name = line.strip('*').strip()
                parent_mod = None
                for mod in self.mods:
                    if name in mod.plugins:
                        parent_mod = mod
                        break

                enabled = False
                if line.startswith('*'):
                    enabled = True
                    parent_mod.enabled = True


                plugin = Plugin(name, enabled, parent_mod)
                # don't manage plugins belonging to disabled mods.
                if parent_mod.enabled and plugin.name not in [i.name for i in self.plugins]:
                    self.plugins.append(plugin)

        return True


    def save_plugins(self):
        """
        responsible for writing Plugins.txt
        """
        with open(self.plugins, "w") as file:
            # only save plugins to Plugins.txt if their parent mod is enabled.
            for plugin in self.plugins:
                file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
        return True


    def print_status(self):
        """
        outputs a list of all mods, then a list of all plugins.
        """
        for index, components in enumerate([self.mods, self.plugins]):
            print()
            print(f" ### | Activated | {'Mod name' if index == 0 else 'Plugin name'}")
            print("-----|-----------|-----")
            for priority, component in enumerate(components):
                num = f"[{priority}]     "
                l = len(str(priority)) + 1
                num = num[0:-l]
                enabled = "[True]     " if component.enabled else "[False]    "
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
        Activate or deactivate a component.
        Returns which plugins need to be added to or removed from self.plugins.
        """
        index = None
        try:
            index = int(mod_index)
            if index < 0:
                raise ValueError
        except ValueError:
            print("Expected a number greater than or equal to 0")
            return False

        # validation
        if mod_type not in ["plugin", "mod"]:
            print(f"expected 'plugin' or 'mod', got arg {mod_type}")
            return False

        components = self.plugins if mod_type == "plugin" else self.mods
        if not len(components):
            print(f"Install mods to '{MODS}' to manage them with oom.")
            print(f"To see your plugins, you must activate the mods they belong to.")
            return False

        if index > len(components) - 1:
            print(f"Expected int 0 through {len(components) - 1} (inclusive)")
            return False

        return components[index].set(state, self.plugins)


    def activate(self, mod_type, mod_index):
        """
        activate a component. Returns success.
        """
        self._set_component_state(mod_type, mod_index, True)
        return True


    def deactivate(self, mod_type, mod_index):
        """
        deactivate a component. Returns success.
        """
        self._set_component_state(mod_type, mod_index, False)
        return True


    def delete(self, mode_index):
        """
        deletes a mod from oom's mod dir. Forces data reload from disk,
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
            # os.system("clear")
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
    expected_dirs = [MODS, CONF_DIR]
    for directory in expected_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # This is where our config will live.
    oom_conf = os.path.join(CONF_DIR, "oom.conf")

    # Create an instance of Oom and run it.
    oom = Oom(oom_conf, PLUGINS)
    exit(oom.run())

