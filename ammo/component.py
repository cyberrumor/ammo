#!/usr/bin/env python3
import os
from typing import Union
from pathlib import Path
from dataclasses import (
    dataclass,
    field,
)


@dataclass(slots=True, kw_only=True)
class Mod:
    location: Path
    game_root: Path
    name: str = field(default_factory=str, init=False)
    visible: bool = field(init=False, default=True, compare=False)
    install_dir: Path = field(init=False)
    enabled: bool = field(init=False, default=False)
    conflict: bool = field(init=False, default=False)
    obsolete: bool = field(init=False, default=True)
    files: list[Path] = field(default_factory=list, init=False)
    modconf: Union[None, Path] = field(init=False, default=None)
    fomod: bool = field(init=False, default=False)
    fomod_target: Path = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.name = self.location.name
        self.install_dir = self.game_root
        self.fomod_target = Path("ammo_fomod")

        # Explicitly set self.files to an empty list in case we're rereshing
        # files via manually calling __post_init__.
        self.files = []
        # Scan the surface level of the mod to determine whether this is a fomod.
        for file in self.location.iterdir():
            if file.is_dir() and file.name.lower() == "fomod":
                # Assign ModuleConfig.xml. Only check surface of fomod folder.
                for f in file.iterdir():
                    if f.name.lower() == "moduleconfig.xml" and f.is_file():
                        self.modconf = f
                        self.fomod = True
                        self.install_dir = self.game_root
                        break
            if self.fomod:
                break

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of an ammo_fomod folder.
        location = self.location
        if self.fomod:
            location /= "ammo_fomod"

        if not location.exists():
            # No files to populate
            return

        # Populate self.files
        for parent_dir, _, files in os.walk(location):
            for file in files:
                f = Path(file)
                loc_parent = Path(parent_dir)
                self.files.append(loc_parent / f)


@dataclass(kw_only=True, slots=True)
class BethesdaMod(Mod):
    game_data: Path
    plugins: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.name = self.location.name
        self.install_dir = self.game_data
        self.fomod_target = Path("ammo_fomod") / self.game_data.name
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
                                    self.install_dir = self.game_root
                                    break
                case False:
                    if file.suffix.lower() == ".dll":
                        self.install_dir = self.game_root

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of an ammo_fomod folder
        # which may or may not exist.
        location = self.location
        if self.fomod:
            location /= "ammo_fomod"

        if not location.exists():
            # No files to populate
            return

        for parent_dir, _, files in os.walk(location):
            for file in files:
                f = Path(file)
                loc_parent = Path(parent_dir)
                self.files.append(loc_parent / f)

        # populate plugins
        plugin_dir = location

        for i in location.iterdir():
            if i.name.lower() == self.game_data.name.lower():
                plugin_dir /= i.name
                break

        if plugin_dir.exists():
            for f in plugin_dir.iterdir():
                if f.suffix.lower() in (".esp", ".esl", ".esm") and not f.is_dir():
                    self.plugins.append(f)


@dataclass(kw_only=True, slots=True)
class Plugin:
    name: str
    mod: Union[None, Mod]
    enabled: bool
    visible: bool = field(init=False, default=True)
    conflict: bool = field(init=False, default=False)


@dataclass(slots=True)
class Download:
    location: Path
    name: str = field(default_factory=str, init=False)
    visible: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        self.name = self.location.name
