#!/usr/bin/env python3
import os
from typing import Union
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


@dataclass(kw_only=True, slots=True)
class Mod:
    location: Path
    parent_data_dir: Path

    visible: bool = field(init=False, default=True)
    modconf: Union[None, Path] = field(init=False, default=None)
    has_data_dir: bool = field(init=False, default=False)
    fomod: bool = field(init=False, default=False)
    enabled: bool = field(init=False, default=False)
    files: list[Path] = field(default_factory=list, init=False)
    plugins: list[str] = field(default_factory=list, init=False)
    name: str = field(default_factory=str, init=False)

    def __post_init__(self):
        # Overrides for whether a mod should install inside Data,
        # or inside the game dir go here.

        # If there is an Edit Scripts folder at the top level,
        # don't put all the mod files inside Data even if there's no
        # Data folder.
        self.name = self.location.name
        if (self.location / "Edit Scripts").exists():
            self.has_data_dir = True

        # Scan the mod, see if this is a fomod, and whether
        # it has a data dir.
        for parent_dir, folders, files in os.walk(self.location):
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

    def associated_plugins(self, plugins) -> list:
        result = []
        for plugin in plugins:
            if any(file.name == plugin.name for file in self.files):
                if plugin not in result:
                    result.append(plugin)
        return result

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


@dataclass(kw_only=True, slots=True)
class Plugin:
    name: str
    mod: Union[None, Mod]
    enabled: bool
    visible: bool = field(init=False, default=True)


@dataclass(slots=True)
class Download:
    location: Path
    name: str = field(default_factory=str, init=False)
    visible: bool = field(init=False, default=True)

    def __post_init__(self):
        self.name = self.location.name
