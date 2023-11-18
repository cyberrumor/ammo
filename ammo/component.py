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


@dataclass(slots=True)
class Mod:
    location: Path

    visible: bool = field(init=False, default=True, compare=False)
    modconf: Union[None, Path] = field(init=False, default=None)
    has_data_dir: bool = field(init=False, default=False)
    fomod: bool = field(init=False, default=False)
    enabled: bool = field(init=False, default=False)
    files: list[Path] = field(default_factory=list, init=False)
    plugins: list[str] = field(default_factory=list, init=False)
    name: str = field(default_factory=str, init=False)

    def __post_init__(self):
        self.name = self.location.name

        # Scan the surface level of the mod to determine whether this mod will
        # need to be installed in game.directory or game.data.
        # Also determine whether this is a fomod.
        for file in self.location.iterdir():
            match file.name.lower():
                case "data":
                    self.has_data_dir = self.has_data_dir or file.is_dir()

                case "edit scripts":
                    self.has_data_dir = self.has_data_dir or file.is_dir()

                case "fomod":
                    # Assign ModuleConfig.xml. Only check surface of fomod folder.
                    for f in file.iterdir():
                        if f.name.lower() == "moduleconfig.xml" and f.is_file():
                            self.modconf = f
                            self.fomod = True
                            break
                case _:
                    if file.suffix.lower() == ".dll":
                        self.has_data_dir = self.has_data_dir or file.is_file()

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of a Data folder which may or may not exist.
        location = self.location
        if self.fomod:
            location = location / "Data"

        # Populate self.files
        for parent_dir, folders, files in os.walk(location):
            for file in files:
                f = Path(file)
                loc_parent = Path(parent_dir)

                if f.suffix.lower() in (".esp", ".esl", ".esm") and not f.is_dir():
                    # Only associate plugins if the plugins are under a data dir.
                    if loc_parent == self.location or loc_parent.name.lower() == "data":
                        self.plugins.append(f.name)

                self.files.append(loc_parent / f)

    def associated_plugins(self, plugins) -> list:
        result = []
        for plugin in plugins:
            if any(file.name == plugin.name for file in self.files):
                if plugin not in result:
                    result.append(plugin)
        return result


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
