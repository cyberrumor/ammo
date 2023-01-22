#!/usr/bin/env python3
import os
from const import *
from mod import Mod, Plugin

class Oom:
    def __init__(self, conf=os.path.join(CONF_DIR, "oom.conf"), plugin_file=PLUGINS):
        self.conf = conf
        self.plugin_file = plugin_file
        self.mods = []
        self.plugins = []

    def load_mods(self):
        """
        Instance a  Mod class for each mod folder in oom's mod directory.
        """
        mods = []
        mod_folders = [i for i in os.listdir(MODS) if os.path.isdir(os.path.join(MODS, i))]
        for mod_folder in mod_folders:
            mod = Mod(mod_folder, os.path.join(MODS, mod_folder), False)
            mods.append(mod)
        self.mods = mods


    def load_mods_from_conf(self):
        """
        Read our conf file. If there's mods in it, put them in order.
        Put mods that aren't listed in the conf file at the end.
        """
        ordered_mods = []
        if not os.path.exists(self.conf):
            return

        with open(self.conf, "r") as file:
            for line in file:
                if line.startswith('#'):
                    continue
                name = line.strip('*').strip()
                enabled = False
                if line.startswith('*'):
                    enabled = True

                if name not in [i.name for i in self.mods]:
                    print(f"we found a mod '{name}' that isn't in {self.conf}. Ignoring.")
                    continue

                for mod in self.mods:
                    if mod.name == name:
                        mod.enabled = enabled
                        ordered_mods.append(mod)
                        break
        for mod in self.mods:
            if mod not in ordered_mods:
                ordered_mods.append(mod)
        self.mods = ordered_mods


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
                    # attempt to enable the parent mod,
                    # only do this if all that mod's files are present.
                    if hasattr(parent_mod, "files_in_place"):
                        if parent_mod.files_in_place():
                            parent_mod.enabled = True 
                    else:
                        print(f"There was an enabled plugin {name} that was missing dependencies!")
                        print("If you want to delete files from a mod, delete them from")
                        print(f"{MODS}")
                        print("instead of from")
                        print(f"{GAME_DIR}")
                        input("[Enter] to try to automatically fix, [CTRL+C] to exit.")
                        # literally just pretend it doesn't exist
                        continue

                plugin = Plugin(name, enabled, parent_mod)
                # don't manage plugins belonging to disabled mods.
                if parent_mod.enabled and plugin.name not in [i.name for i in self.plugins]:
                    self.plugins.append(plugin)

        return True


    def save_order(self):
        """
        Writes oom.conf and Plugins.txt.
        """
        with open(self.plugin_file, "w") as file:
            for plugin in self.plugins:
                file.write(f"{'*' if plugin.enabled else ''}{plugin.name}\n")
        with open(self.conf, "w") as file:
            for mod in self.mods:
                file.write(f"{'*' if mod.enabled else ''}{mod.name}\n")
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
            # "delete": "delete a mod and its plugins. Forces config reload from disk. Usage: delete <index>",
            "move": "move a component from index to index. Usage: move mod|plugin <from_index> <to_index>",
            "exit": "quit oom without applying changes.",
        }.items():
            print(f"{k}: {v}")
        print()
        input("[Enter] to continue")
        return True


    def _get_validated_components(self, mod_type, mod_index):
        index = None
        try:
            index = int(mod_index)
            if index < 0:
                raise ValueError
        except ValueError:
            print("Expected a number greater than or equal to 0")
            return False

        if mod_type not in ["plugin", "mod"]:
            print(f"expected 'plugin' or 'mod', got arg {mod_type}")
            return False
        components = self.plugins if mod_type == "plugin" else self.mods
        if not len(components):
            print(f"Install mods to '{MODS}' to manage them with oom.")
            print(f"To see your plugins, you must activate the mods they belong ot.")
            return False

        if index > len(components) - 1:
            print(f"Expected int 0 through {len(components) - 1} (inclusive)")
            return False

        return components


    def _set_component_state(self, mod_type, mod_index, state):
        """
        Activate or deactivate a component.
        Returns which plugins need to be added to or removed from self.plugins.
        """
        components = self._get_validated_components(mod_type, mod_index)
        if not components:
            input("[Enter]")
            return False

        return components[int(mod_index)].set(state, self.plugins)


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
        components = None
        for index in [old_mod_index, new_mod_index]:
            components = self._get_validated_components(mod_type, index)
            if not components:
                return False

        old_ind = int(old_mod_index)
        new_ind = int(new_mod_index)

        component = components.pop(old_ind)
        components.insert(new_ind, component)

        return True


    def _clean_data_dir(self):
        """
        Removes all symlinks and deletes empty folders.
        """
        for tree in os.walk(GAME_DIR):
            dirpath = tree[0]
            dirnames = tree[1]
            filenames = tree[2]
            for file in filenames:
                full_path = os.path.join(dirpath, file.lower())
                if os.path.islink(full_path):
                    os.unlink(full_path)
        
            if not dirnames and not filenames:
                os.rmdir(dirpath)


    def stage(self):
        """
        Returns a dict containing the final symlinks that will be installed.
        """
        # src: dest
        result = {}
        for mod in [i for i in self.mods if i.enabled]:
            for src in mod.files.values():
                corrected_name = src.split(mod.name, 1)[-1]
                dest = os.path.join(GAME_DIR, corrected_name.lower().replace('/data', 'Data').lstrip('/'))
                result[src] = dest
        return result


    def commit(self):
        """
        Makes changes persist on disk.
        """
        self.save_order()
        stage = self.stage()
        self._clean_data_dir()

        for src, dest in stage.items():
            os.makedirs(os.path.split(dest)[0], exist_ok=True)
            os.symlink(src, dest)

        return True


    def run(self):
        # complete setup
        self.load_mods()
        self.load_mods_from_conf()
        self.load_plugins()

        self.command = {
            # cmd: (method, len(args))
            "help": {"func": self.help, "num_args": 0},
            "activate": {"func": self.activate, "num_args": 2},
            "deactivate": {"func": self.deactivate, "num_args": 2},
            "move": {"func": self.move, "num_args": 3},
            "commit": {"func": self.commit, "num_args": 0},
            # "delete": {"func": self.delete, "num_args": 1},
            "clean": {"func": self._clean_data_dir, "num_args": 0},
            "exit": {"func": exit, "num_args": 0},
        }

        cmd = ""
        try:
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

        except KeyboardInterrupt:
            exit()


if __name__ == "__main__":
    # Create expected directories if they don't alrady exist.
    expected_dirs = [MODS, CONF_DIR]
    for directory in expected_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)


    # Create an instance of Oom and run it.
    oom = Oom()
    exit(oom.run())

