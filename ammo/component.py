#!/usr/bin/env python3
import os
from typing import Union
from pathlib import Path
from dataclasses import (
    dataclass,
    field,
)


@dataclass(kw_only=True, slots=True)
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
    replacements: dict[str, str] = field(init=False, default_factory=dict)

    def find_module_conf(self, location) -> Path | None:
        """
        Recursively scan for a ModuleConfig.xml file
        and return the absolute path to it.
        """
        if location.is_file() and location.name.lower() == "moduleconfig.xml":
            return location.resolve()

        if location.is_dir():
            for file in location.iterdir():
                result = self.find_module_conf(file)
                if result is not None:
                    return result

    def __post_init__(self) -> None:
        self.name = self.location.name
        self.install_dir = self.game_root
        self.fomod_target = Path("ammo_fomod")
        self.replacements = {}

        # Explicitly set self.files to an empty list in case we're rereshing
        # files via manually calling __post_init__.
        self.files = []
        # Scan the surface level of the mod to determine whether this is a fomod.
        self.modconf = self.find_module_conf(self.location)

        if self.modconf is not None:
            self.fomod = True

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of an ammo_fomod folder.
        location = self.location
        if self.fomod:
            # ModuleConfig.xml uses locations relative to the directory
            # that contains fomod/ModuleConfig.xml. Set self.location to
            # this directory so locations referenced in ModuleConfig.xml
            # resolve correctly.
            location = self.modconf.parent.parent / "ammo_fomod"

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
    game_pak: Path
    plugins: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.name = self.location.name
        self.install_dir = self.game_data
        self.fomod_target = Path("ammo_fomod") / self.game_data.name

        self.replacements = {
            "binaries": "Binaries",
            "content": "Content",
            "data files": "Data Files",
            "data": "Data",
            "dev": "Dev",
            "docs": "Docs",
            "dyndolod": "DynDOLOD",
            "edit scripts": "Edit Scripts",
            "mockgame": "MockGame",
            "netscriptframework": "NetScriptFramework",
            "oblivionremastered": "OblivionRemastered",
            "obvdata": "ObvData",
            "paks": "Paks",
            "plugins": "Plugins",
            "scripts": "Scripts",
            "skse": "SKSE",
            "source": "Source",
        }

        # Explicitly set self.files to an empty list in case we're rereshing
        # files via manually calling __post_init__.
        self.files = []
        # Scan the surface level of the mod to determine whether this mod will
        # need to be installed in game.directory, game.data, or game.pak.
        # Also determine whether this is a fomod.
        for file in self.location.iterdir():
            match file.is_dir():
                case True:
                    match file.name.lower():
                        case (
                            "data"
                            | "data files"
                            | "edit scripts"
                            | "oblivionremastered"
                        ):
                            self.install_dir = self.game_root

                        case "~mods":
                            # This will only be true for Oblivion Remastered, and potentially
                            # also future UE5 Bethesda games. It's unlikely that this directory
                            # will be used by mods for non-UE5 games, so no need to hide this
                            # behind a game name condition.
                            self.install_dir = self.game_pak.parent

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

                    if file.suffix.lower() == ".pak":
                        self.install_dir = self.game_pak

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

        # Find the folder that plugins should be populated from.
        # Start from the game directory or the ammo_fomod directory.
        plugin_dir = location

        # See if there's a Data folder nested in here anywhere.
        for parent_dir, folders, files in os.walk(location):
            for folder in folders:
                if folder.lower() == self.game_data.name.lower():
                    plugin_dir = Path(parent_dir) / folder
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


@dataclass(slots=True)
class Tool:
    path: Path
    visible: bool = True
