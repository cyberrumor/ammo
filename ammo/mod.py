#!/usr/bin/env python3
import os
from pathlib import (
    Path,
    PurePath,
)
from dataclasses import (
    dataclass,
    field,
)


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
    location: Path
    sane: bool = False

    def __post_init__(self):
        if all(((i.isalnum() or i in [".", "_", "-"]) for i in self.name)):
            self.sane = True

    def __str__(self):
        return self.name


@dataclass
class Mod:
    name: str
    location: Path
    parent_data_dir: Path

    modconf: None | Path = None
    has_data_dir: bool = False
    fomod: bool = False
    is_dlc: bool = False
    enabled: bool = False

    files: dict[Path] = field(default_factory=dict)
    plugins: list[str] = field(default_factory=list)

    def populate_from(self, parent_dir, files):
        """
        Takes a parent directory and a list of files. If the file is a plugin,
        ensure it's in the proper place before adding it to self.files.
        If it's not a plugin, always add it.
        """
        for file in files:
            f = Path(file)
            loc_parent = Path(parent_dir)

            if f.suffix.lower() in [".esp", ".esl", ".esm"]:
                if loc_parent != self.location and loc_parent != self.location / "Data":
                    # Skip plugins in the wrong place
                    continue
                self.plugins.append(file)
                self.files[file] = loc_parent / f
                continue
            self.files[file] = loc_parent / f

    def __post_init__(self):
        # Overrides for whether a mod should install inside Data,
        # or inside the game dir go here.

        # If there is an Edit Scripts folder at the top level,
        # don't put all the mod files inside Data even if there's no
        # Data folder.
        if (self.location / "Edit Scripts").exists():
            self.has_data_dir = True

        # Get the files, set some flags.
        for parent_dir, folders, files in os.walk(self.location):
            loc_parent = Path(parent_dir)
            # If there is a data dir, remember it.
            if loc_parent in [
                self.location / "Data",
                self.location / "data",
            ]:
                self.has_data_dir = True

            if "fomod" in [i.lower() for i in folders]:
                # find the ModuleConfig.xml if it exists.
                for parent, _dirs, filenames in os.walk(self.location):
                    p = Path(parent)
                    for filename in filenames:
                        if filename.lower() == "moduleconfig.xml":
                            self.modconf = p / filename
                            self.fomod = True
                            break

                    if self.fomod:
                        break

            # Find plugin in the Data folder or top level and add them to self.plugins.
            if not self.fomod:
                for file in files:
                    self.populate_from(parent_dir, files)

        # Fomods only get stuff insalled if it's beneath the data folder.
        if self.fomod:
            for parent_dir, folders, files in os.walk(self.location / "Data"):
                self.populate_from(parent_dir, files)

        else:
            # If there is a DLL that's not inside SKSE/Plugins, it belongs in the game dir.
            # Don't do this to fomods because they might put things in a different location,
            # then associate them with SKSE/Plugins in the 'destination' directive.
            for parent_dir, folders, files in os.walk(self.location):
                if self.has_data_dir:
                    break
                for file in files:
                    p = Path(file)
                    if p.suffix.lower() == ".dll":
                        # This needs more robust handling.
                        if "se/plugins" not in parent_dir.lower():
                            self.has_data_dir = True
                            break

    def __str__(self):
        return f'{"[True]     " if self.enabled else "[False]    "}{self.name}'

    def associated_plugins(self, plugins):
        return [
            plugin for plugin in plugins for file in self.files if file == plugin.name
        ]

    def files_in_place(self):
        """
        For each file in ~/.local/ammo/{game}/mods/{mod}, check that the file
        also exists relative to the game's directory. If all files exist,
        return True. Otherwise False.
        """
        for path in self.files.values():
            corrected_location = os.path.join(
                str(path).split(self.name, 1)[-1].strip("/"), self.parent_data_dir
            )
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
