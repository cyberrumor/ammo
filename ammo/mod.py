#!/usr/bin/env python3
import os
from dataclasses import dataclass, field

@dataclass
class DLC:
    name: str
    enabled: bool = True
    is_dlc: bool = True

    def __str__(self):
        return self.name

    def files_in_place(self):
        return True


@dataclass
class Download:
    name: str
    location: str
    sane: bool = False

    def __post_init__(self):
        if all([(i.isalnum() or i in ['.', '_', '-']) for i in self.name]):
            self.sane = True

    def __str__(self):
        return self.name


@dataclass
class Mod:
    name: str
    location: str
    parent_data_dir: str

    modconf: str = ""

    data_dir: bool = False
    fomod: bool = False
    is_dlc: bool = False
    enabled: bool = False

    files: dict[str] = field(default_factory=dict)
    plugins: list[str] = field(default_factory=list)


    def __post_init__(self):
        # Overrides for whether a mod should install inside Data,
        # or inside the game dir go here.

        # If there is an Edit Scripts folder at the top level,
        # don't put all the mod files inside Data even if there's no
        # Data folder.
        if os.path.exists(os.path.join(self.location, "Edit Scripts")):
            self.data_dir = True

        # If there is a DLL that's not inside SKSE/Plugins, it belongs in the game dir.
        for parent_dir, folder, files in os.walk(self.location):
            if self.data_dir:
                break
            for file in files:
                if os.path.splitext(file)[-1].lower() == ".dll":
                    # This needs more robust handling.
                    self.data_dir = True
                    break

        # Get the files, set some flags.
        for parent_dir, folders, files in os.walk(self.location):
            # If there is a data dir, remember it.
            if parent_dir == os.path.join(self.location, 'Data'):
                self.data_dir = True

            if folders and "fomod" in [i.lower() for i in folders]:
                self.fomod = True
                # find the ModuleConfig.xml if it exists.
                for parent, dirs, files in os.walk(self.location):
                    for file in files:
                        if file.lower() == "moduleconfig.xml":
                            self.modconf = os.path.join(parent, file)
                            break
                    if self.modconf:
                        break

            for file in files:
                self.files[file] = os.path.join(parent_dir, file)
                if os.path.splitext(file)[-1] in ['.esp', '.esl', '.esm'] \
                and file not in self.plugins \
                and (parent_dir == self.location or parent_dir == os.path.join(self.location, 'Data')):
                    self.plugins.append(file)

        # if this is a configured fomod, don't install anything above the "Data" folder.
        if self.fomod:
            self.files.clear()
            for parent_dir, folders, files in os.walk(os.path.join(self.location, "Data")):
                for file in files:
                    self.files[file] = os.path.join(parent_dir, file)


    def __str__(self):
        return f'{"[True]     " if self.enabled else "[False]    "}{self.name}'


    def associated_plugins(self, plugins):
        return [plugin for plugin in plugins for file in self.files if file == plugin.name]


    def files_in_place(self):
        for location in self.files.values():
            corrected_location = os.path.join(location.split(self.name, 1)[-1].strip('/'), self.parent_data_dir)
            # note that we don't care if the files are the same here, just that the paths and
            # filenames are the same. It's fine if the file comes from another mod.
            if not os.path.exists(corrected_location):
                print(f"unable to find expected file '{corrected_location}'")
                return False
        return True


@dataclass
class Plugin:
    name: str
    enabled: bool
    parent_mod: str

    def __str__(self):
        return f'{"[True]     " if self.enabled else "[False]    "}{self.name}'


