#!/usr/bin/env python3
import sys
import os
from const import *


def is_plugin(file):
    return any([
        file.endswith(i) for i in [".esp", ".esl", ".esm"]
    ])


class Mod:
    def __init__(self, name, location, enabled):
        self.name = name
        self.location = location
        self.data_dir = False
        self.enabled = enabled
        self.files = {}
        self.plugins = []
        self.visible = True

        # get our files
        for struct in os.walk(self.location):
            # if we have a data dir, remember it.
            parent_dir = struct[0]
            folders = struct[1]
            files = struct[2]


        # get our files
        for struct in os.walk(self.location):
            # if we have a data dir, remember it.
            parent_dir = struct[0]
            folders = struct[1]
            files = struct[2]

            if folders and "data" in [i.lower() for i in folders]:
                self.data_dir = True

            for file in files:
                self.files[file] = os.path.join(parent_dir, file)

                if is_plugin(file) and file not in self.plugins:
                    self.plugins.append(file)


    def associated_plugins(self, plugins):
        owned = []
        for file in self.files:
            for plugin in plugins:
                if file == plugin.name:
                    owned.append(plugin)
        return owned


    def set(self, state, oom_plugins):
        self.enabled = state
        if self.enabled:
            for name in self.plugins:
                if name not in [i.name for i in oom_plugins]:
                    plugin = Plugin(name, False, self)
                    oom_plugins.append(plugin)
        else:
            for plugin in self.associated_plugins(oom_plugins):
                plugin.enabled = False if state == False else plugin.enabled

            if plugin in oom_plugins:
                oom_plugins.remove(plugin)
        return True


    def files_in_place(self):
        for location in self.files.values():
            corrected_location = os.path.join(location.split(self.name, 1)[-1].strip('/'), DATA)
            # note that we don't care if the files are the same here, just that the paths and
            # filenames are the same. It's fine if our file comes from another mod.
            if not os.path.exists(corrected_location):
                print(f"unable to find expected file '{corrected_location}'")
                return False
        return True


class Plugin:
    def __init__(self, name, enabled, parent_mod):
        self.name = name
        self.enabled = enabled
        self.parent_mod = parent_mod

        if parent_mod == None:
            print(f"Plugin {self.name} was found in Plugins.txt but is not owned by a mod.")
            print(f"Please refrain from renaming plugins.")
            print(f"oom only supports managing plugins from {MOD}.")
            input("[Enter]")
            exit()

    def set(self, state, plugins):
        if state and self.parent_mod.enabled == state:
            self.enabled = state
            return True
        if state and not self.parent_mod.enabled:
            print(f"Error: This is owned by disabled mod {self.parent_mod.name}.")
            print("Please enable that mod first, then try this again.")
            input("[Enter]")
            return False

        self.enabled = state
        return [self.name]




