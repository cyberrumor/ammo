#!/usr/bin/env python3
import os
from typing import (
    Callable,
    Union,
)
from pathlib import Path
from dataclasses import (
    dataclass,
    field,
)

from .lib import casefold_path


@dataclass(frozen=True, kw_only=True)
class Game:
    ammo_conf: Path
    ammo_log: Path
    ammo_mods_dir: Path
    ammo_tools_dir: Path
    name: str
    directory: Path


@dataclass(frozen=True, kw_only=True)
class BethesdaGame(Game):
    data: Path
    dlc_file: Path
    plugin_file: Path
    enabled_formula: Callable[[str], bool] = field(
        default=lambda line: line.strip().startswith("*")
    )
    # unreal engine 5 games expect a Paks directory:
    # <ProjectName>/Content/Paks/ - This is the primary location for pak files specific to your project.
    #                               For some games, this also includes a ~mods directory at the end.
    # Engine/Content/Paks/        - This location contains pak files that are part of the Unreal Engine itself.
    # Saved/Content/Paks/         - This location is typically for pak files related to game saves or other
    #                               runtime-generated content.
    # This variable refers to the <ProjectName>/Content/Paks/[~mods] directory.
    # https://docs.mod.io/guides/ue-mod-loading
    # Rust Traits would be a more correct solution than just putting this on every bethesda game -_-.
    pak: Path = field(init=False, default_factory=Path)
    dll: Path = field(init=False, default_factory=Path)

    def __post_init__(self):
        # Get past dataclasses.FrozenInstanceError produced by direct assignment via object.__setattr__.
        object.__setattr__(
            self,
            "pak",
            self.directory / self.name.replace(" ", "") / "Content" / "Paks" / "~mods",
        )

        object.__setattr__(
            self,
            "dll",
            self.directory / self.name.replace(" ", "") / "Binaries" / "Win64",
        )


@dataclass(kw_only=True, slots=True)
class Mod:
    location: Path
    game_root: Path
    name: str = field(default_factory=str, init=False)
    visible: bool = field(init=False, default=True, compare=False)
    enabled: bool = field(init=False, default=False)
    conflict: bool = field(init=False, default=False)
    obsolete: bool = field(init=False, default=True)
    files: dict[Path, Path] = field(default_factory=dict, init=False)
    modconf: Union[None, Path] = field(init=False, default=None)
    fomod: bool = field(init=False, default=False)
    fomod_target: Union[None, Path] = field(init=False, default=None)
    replacements: dict[str, str] = field(init=False, default_factory=dict)
    tags: list[str] = field(init=False, default_factory=list)

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
        self.fomod_target = Path("ammo_fomod")
        self.replacements = {}

        # Explicitly set self.files to an empty dict in case we're rereshing
        # files via manually calling __post_init__.
        self.files = {}
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

        self.populate_files(location, self.game_root)

    def populate_files(self, location: Path, install_dir: Path):
        """
        Populate self.files
        """
        for parent_dir, _, files in os.walk(location):
            p = Path(parent_dir)
            relative_parent = (install_dir / p.relative_to(location)).relative_to(
                self.game_root
            )
            for file in files:
                relative_dest = casefold_path(
                    self.replacements, Path("."), relative_parent / file
                )
                self.files[relative_dest] = p / file


@dataclass(kw_only=True, slots=True)
class BethesdaMod(Mod):
    game_data: Path
    game_pak: Path
    game_dll: Path
    plugins: list[Path] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.name = self.location.name
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
            "lightplacer": "LightPlacer",
            "mockgame": "MockGame",
            "netscriptframework": "NetScriptFramework",
            "oblivionremastered": "OblivionRemastered",
            "obse": "OBSE",
            "obvdata": "ObvData",
            "paks": "Paks",
            "plugins": "Plugins",
            "scripts": "Scripts",
            "skse": "SKSE",
            "skypatcher": "SkyPatcher",
            "source": "Source",
            "win64": "Win64",
            "interface": "Interface",
            "infinityui": "InfinityUI",
            "map": "Map",
            "worldmap": "WorldMap",
            "localmapmenu": "LocalMapMenu",
        }

        # Explicitly set self.files to an empty dict in case we're rereshing
        # files via manually calling __post_init__.
        self.files = {}
        # Scan the surface level of the mod to determine whether this mod will
        # need to be installed in game.directory, game.data, or game.pak.
        # Also determine whether this is a fomod.
        install_dir = self.game_data
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
                            # We can't break early here in case we later detect fomod,
                            # in which case self.modconf wouldn't be assigned.
                            install_dir = self.game_root

                        case "~mods":
                            # This will only be true for Oblivion Remastered, and potentially
                            # also future UE5 Bethesda games. It's unlikely that this directory
                            # will be used by mods for non-UE5 games, so no need to hide this
                            # behind a game name condition. We can't break early here in case
                            # the mod is ckpe_loader.exe.
                            install_dir = self.game_pak.parent

                        case "fomod":
                            # Assign ModuleConfig.xml. Only check surface of fomod folder.
                            for f in file.iterdir():
                                if f.name.lower() == "moduleconfig.xml" and f.is_file():
                                    self.modconf = f
                                    self.fomod = True
                                    install_dir = self.game_root
                                    break
                case False:
                    if file.suffix.lower() == ".dll":
                        install_dir = self.game_dll
                        break

                    if file.suffix.lower() == ".pak":
                        install_dir = self.game_pak
                        break

                    # handle creation kit platform extended, which is not
                    # packaged as a fomod. Otherwise it goes to self.game_pak,
                    # which is incorrect. We don't need to check other
                    # conditions if we hit this.
                    if file.name.lower() == "ckpe_loader.exe":
                        install_dir = self.game_root
                        break

        # Determine which folder to populate self.files from. For fomods, only
        # care about files inside of an ammo_fomod folder
        # which may or may not exist.
        location = self.location
        if self.fomod:
            location /= "ammo_fomod"

        if not location.exists():
            # No files to populate
            return

        self.populate_files(location, install_dir)

        # Find the folder that plugins should be populated from.
        # Start from the game directory or the ammo_fomod directory.
        plugin_dir = location

        # See if there's a Data folder nested in here anywhere.
        for dest, src in self.files.items():
            if dest.parent.name == self.game_data.name:
                plugin_dir = src.parent
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
