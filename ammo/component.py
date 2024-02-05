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
    PLUGIN = "plugin"


class RenameEnum(str, Enum):
    MOD = "mod"
    DOWNLOAD = "download"


@dataclass(slots=True, kw_only=True)
class Mod:
    location: Path
    game_root: Path
    game_data: Path

    visible: bool = field(init=False, default=True, compare=False)
    modconf: Union[None, Path] = field(init=False, default=None)
    install_dir: Path = field(init=False)
    fomod: bool = field(init=False, default=False)
    enabled: bool = field(init=False, default=False)
    conflict: bool = field(init=False, default=False)
    files: list[Path] = field(default_factory=list, init=False)
    plugins: list[str] = field(default_factory=list, init=False)
    name: str = field(default_factory=str, init=False)

    def __post_init__(self) -> None:
        self.name = self.location.name
        self.install_dir = self.game_data
        # Explicitly set self.files to an empty list in case we're rereshing
        # files via manually calling __post_init__.
        self.files = []
        # Scan the surface level of the mod to determine whether this mod will
        # need to be installed in game.directory or game.data.
        # Also determine whether this is a fomod.
        for file in self.location.iterdir():
            match file.is_dir():
                case True:
                    match file.name.lower():
                        case "data" | "data files":
                            self.install_dir = self.game_root

                        case "edit scripts":
                            self.install_dir = self.game_root

                        case "fomod":
                            # Assign ModuleConfig.xml. Only check surface of fomod folder.
                            for f in file.iterdir():
                                if f.name.lower() == "moduleconfig.xml" and f.is_file():
                                    self.modconf = f
                                    self.fomod = True
                                    break
                case False:
                    if file.suffix.lower() == ".dll":
                        self.install_dir = self.game_root

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of a game_data.name folder which may or may not exist.
        location = self.location
        if self.fomod:
            location = location / self.game_data.name

        # Populate self.files
        for parent_dir, _, files in os.walk(location):
            for file in files:
                f = Path(file)
                loc_parent = Path(parent_dir)

                if f.suffix.lower() in (".esp", ".esl", ".esm") and not f.is_dir():
                    # Only associate plugins if the plugins are under a data dir.
                    if (
                        loc_parent == self.location
                        or loc_parent.name.lower() == self.game_data.name.lower()
                    ):
                        self.plugins.append(f.name)

                self.files.append(loc_parent / f)


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

    def __post_init__(self) -> None:
        self.name = self.location.name
