#!/usr/bin/env python3
import re
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from pathlib import Path
from .mod_controller import (
    Game,
    ModController,
)
from .ui import (
    Controller,
    UI,
)


class Source(str, Enum):
    UNKNOWN = "unknown"
    STEAM = "steam"
    FLATPAK = "flatpak"


@dataclass(frozen=True, kw_only=True)
class GameSelection:
    name: field(default_factory=str)
    source: field(default_factory=Source)
    library: field(default_factory=Path, repr=False)


class GameController(Controller):
    """
    GameController is responsible for selecting games.
    If there is only one valid game, it is selected automatically,
    in which case users won't see this menu.

    Once a game is selected, GameController launches ModController
    with the selected game and runs it under the UI.
    """

    def __init__(self):
        self.ids = {
            "Skyrim Special Edition": "489830",
            "Oblivion": "22330",
            "Fallout 4": "377160",
            "Skyrim": "72850",
            "Enderal": "933480",
            "Enderal Special Edition": "976620",
            "Starfield": "1716740",
        }
        self.downloads = Path.home() / "Downloads"
        self.steam = Path.home() / ".local/share/Steam/steamapps"
        self.flatpak = (
            Path.home()
            / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps"
        )
        self.libraries: list[Path] = []
        self.games: list[GameSelection] = []

        for source in [self.steam, self.flatpak]:
            if (source / "libraryfolders.vdf").exists() is False:
                continue

            with open(source / "libraryfolders.vdf", "r") as libraries_file:
                library_paths = re.findall(r'"path"\s+"(\S+)"', libraries_file.read())
                self.libraries.extend(
                    [
                        Path(library) / "steamapps"
                        for library in library_paths
                        if Path(library).exists()
                    ]
                )

        for library in self.libraries:
            common_path = library / "common"
            if common_path.exists():
                for game in common_path.iterdir():
                    if game.name not in self.ids:
                        continue

                    source = Source.UNKNOWN
                    if self.steam in [library, library.parents]:
                        source = Source.STEAM
                    elif self.flatpak in [library, library.parents]:
                        source = Source.FLATPAK

                    game_selection = GameSelection(
                        name=game.name,
                        source=source,
                        library=library,
                    )

                    self.games.append(game_selection)

        if len(self.games) == 0:
            raise FileNotFoundError(
                f"Supported games {list(self.ids)} not found in {self.libraries}"
            )
        elif len(self.games) == 1:
            self._manage_game(0)
        else:
            self._populate_index_commands()

    def _prompt(self) -> str:
        return super()._prompt()

    def _post_exec(self) -> bool:
        # When we're done managing a game, just quit.
        return True

    def __str__(self) -> str:
        result = ""
        result += " index | Game\n"
        result += "-------|-----\n"
        for i, game in enumerate(self.games):
            index = f"[{i}]"
            result += f"{index:<7} {game.name} ({game.source.value})\n"
        return result

    def _populate_index_commands(self):
        """
        Hack to get methods named after numbers,
        one for each selectable option.
        """
        for i, game in enumerate(self.games):
            setattr(self, str(i), lambda self, i=i: self._manage_game(i))
            full_location = str((game.library / "common" / game.name)).replace(
                str(Path.home()), "~", 1
            )
            self.__dict__[str(i)].__doc__ = full_location

    def _manage_game(self, index: int):
        """
        Gather paths for the game at <index>. Create an instance of
        ModController for that game, then run it under the UI.
        """
        game_selection = self.games[index]

        app_id = self.ids[game_selection.name]
        pfx = game_selection.library / f"compatdata/{app_id}/pfx"
        directory = game_selection.library / f"common/{game_selection.name}"
        app_data = (
            game_selection.library / f"{pfx}/drive_c/users/steamuser/AppData/Local"
        )
        dlc_file = app_data / f"{game_selection.name.replace('t 4', 't4')}/DLCList.txt"
        plugin_file = (
            app_data / f"{game_selection.name.replace('t 4', 't4')}/Plugins.txt"
        )
        data = directory / "Data"
        if game_selection.source == Source.FLATPAK:
            ammo_conf_dir = Path.home() / f".var/app/com.valvesoftware.Steam/.local/share/ammo/{game_selection.name}"
        elif game_selection.source == Source.STEAM:
            ammo_conf_dir = Path.home() / f".local/share/ammo/{game_selection.name}"
        else:
            raise TypeError(
                f"Expected {list(Source)} but got {game_selection.source} of type {type(game_selection.source)}"
            )
        ammo_mods_dir = ammo_conf_dir / "mods"
        ammo_conf = ammo_conf_dir / "ammo.conf"

        game = Game(
            game_selection.name,
            directory,
            data,
            ammo_conf,
            dlc_file,
            plugin_file,
            ammo_mods_dir,
        )

        # Launch the main mod organizer.
        controller = ModController(self.downloads, game)
        ui = UI(controller)
        ui.repl()
