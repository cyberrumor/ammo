#!/usr/bin/env python3
import os

class DLC:
    def __init__(self, name):
        self.enabled = True
        self.name = name
        self.is_dlc = True


    def files_in_place(self):
        return True


class Download:
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.sane = False
        if all([(i.isalnum() or i in ['.', '_', '-']) for i in self.name]):
            self.sane = True


    def sanitize(self):
        """
        This will make the download's name compatible with
        our os.system(7z) call. We need this because of filenames
        that contain quotes.
        """
        fixed_name = self.name.replace(' ', '_')
        fixed_name = ''.join(
            [i for i in fixed_name if i.isalnum() or i in ['.', '_', '-']]
        )
        parent_folder = os.path.split(self.location)[0]
        new_location = os.path.join(parent_folder, fixed_name)
        os.rename(self.location, new_location)
        self.location = new_location
        self.name = fixed_name
        self.sane = True


class Mod:
    def __init__(self, name, location, parent_data_dir, enabled):
        self.name = name
        self.location = location
        self.parent_data_dir = parent_data_dir
        self.data_dir = False
        self.fomod = False
        self.is_dlc = False
        self.enabled = enabled
        self.files = {}
        self.plugins = []

        # get our files
        for parent_dir, folders, files in os.walk(self.location):
            # if we have a data dir, remember it.
            if folders and "data" in [i.lower() for i in folders]:
                self.data_dir = True

            if folders and "fomod" in [i.lower() for i in folders]:
                self.fomod = True

            for file in files:
                self.files[file] = os.path.join(parent_dir, file)
                if os.path.splitext(file)[-1] in ['.esp', '.esl', '.esm'] \
                and file not in self.plugins \
                and (parent_dir == self.location or parent_dir == os.path.join(self.location, 'Data')):
                    self.plugins.append(file)


    def associated_plugins(self, plugins):
        owned = []
        for file in self.files:
            for plugin in plugins:
                if file == plugin.name:
                    owned.append(plugin)
        return owned


    def set(self, state, ammo_plugins):
        if self.fomod:
            print("This is a fomod. Please manually create proper Data structure in")
            print(f"{self.location}")
            print("then refresh and try again.")
            return False

        self.enabled = state
        if self.enabled:
            for name in self.plugins:
                if name not in [i.name for i in ammo_plugins]:
                    plugin = Plugin(name, False, self)
                    ammo_plugins.append(plugin)
        else:
            for plugin in self.associated_plugins(ammo_plugins):
                plugin.enabled = False if state == False else plugin.enabled

                if plugin in ammo_plugins:
                    ammo_plugins.remove(plugin)
        return True


    def files_in_place(self):
        for location in self.files.values():
            corrected_location = os.path.join(location.split(self.name, 1)[-1].strip('/'), self.parent_data_dir)
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




