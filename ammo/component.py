#!/usr/bin/env python3
import os
from enum import Enum
from pathlib import Path
from dataclasses import (
    dataclass,
    field,
)


class ComponentEnum(str, Enum):
    MOD = "mod"
    PLUGIN = "plugin"


class DeleteEnum(str, Enum):
    MOD = "mod"
    DOWNLOAD = "download"


@dataclass
class DLC:
    name: str
    enabled: bool = True
    is_dlc: bool = True
    visible: bool = True

    def files_in_place(self):
        return True


@dataclass
class Plugin:
    name: str
    enabled: bool
    parent_mod: str
    visible: bool = True


@dataclass
class Download:
    name: str
    location: Path
    sane: bool = False
    visible: bool = True

    def __post_init__(self):
        if all(((i.isalnum() or i in [".", "_", "-"]) for i in self.name)):
            self.sane = True


@dataclass
class Mod:
    name: str
    location: Path
    parent_data_dir: Path

    visible: bool = True
    modconf: None | Path = None
    has_data_dir: bool = False
    fomod: bool = False
    is_dlc: bool = False
    enabled: bool = False

    files: list[Path] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Overrides for whether a mod should install inside Data,
        # or inside the game dir go here.

        # If there is an Edit Scripts folder at the top level,
        # don't put all the mod files inside Data even if there's no
        # Data folder.
        if (self.location / "Edit Scripts").exists():
            self.has_data_dir = True

        # Scan the mod, see if this is a fomod, and whether
        # it has a data dir.
        for parent_dir, folders, files in os.walk(self.location):
            if self.fomod and self.has_data_dir:
                break

            loc_parent = Path(parent_dir)
            if loc_parent in [
                self.location / "Data",
                self.location / "data",
            ]:
                self.has_data_dir = True

            fomod_dirs = [i for i in folders if i.lower() == "fomod"]
            if not fomod_dirs:
                continue
            fomod_dir = fomod_dirs.pop()
            # find the ModuleConfig.xml if it exists.
            for parent, _dirs, filenames in os.walk(self.location / fomod_dir):
                if self.fomod:
                    break
                p = Path(parent)
                for filename in filenames:
                    if filename.lower() == "moduleconfig.xml":
                        self.modconf = p / filename
                        self.fomod = True
                        break

        location = self.location
        if self.fomod:
            location = location / "Data"

        # Populate self.files
        for parent_dir, folders, files in os.walk(location):
            for file in files:
                f = Path(file)
                loc_parent = Path(parent_dir)

                if f.suffix.lower() in (".esp", ".esl", ".esm"):
                    if loc_parent != self.location and loc_parent not in [
                        self.location / "Data",
                        self.location / "data",
                    ]:
                        # Skip plugins in the wrong place
                        continue
                    self.plugins.append(file)
                self.files.append(loc_parent / f)

        if not self.fomod and not self.has_data_dir:
            # If there is a DLL that's not inside SKSE/Plugins, it belongs in the game dir.
            # Don't do this to fomods because they might put things in a different location,
            # then associate them with SKSE/Plugins in the 'destination' directive.
            for parent_dir, folders, files in os.walk(self.location):
                if self.has_data_dir:
                    break
                for file in files:
                    if file.lower().endswith(".dll"):
                        # This needs more robust handling.
                        if not parent_dir.lower().endswith("se/plugins"):
                            self.has_data_dir = True
                            break

    def associated_plugins(self, plugins):
        return [
            plugin
            for plugin in plugins
            for file in self.files
            if file.name == plugin.name
        ]

    def files_in_place(self):
        """
        For each file in ~/.local/ammo/{game}/mods/{mod}, check that the file
        also exists relative to the game's directory. If all files exist,
        return True. Otherwise False.
        """
        for path in self.files:
            corrected_location = os.path.join(
                str(path).split(self.name, 1)[-1].strip("/"), self.parent_data_dir
            )
            # note that we don't care if the files are the same here, just that the paths and
            # filenames are the same. It's fine if the file comes from another mod.
            if not os.path.exists(corrected_location):
                print(f"unable to find expected file '{corrected_location}'")
                return False
        return True
