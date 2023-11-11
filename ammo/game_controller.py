#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from .mod_controller import (
    Game,
    ModController,
)
from .ui import (
    Controller,
    UI,
)


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
        self.libraries = []
        self.games = []

        # parse steam libraries and look for games
        with open(self.steam / "libraryfolders.vdf", "r") as libraries_file:
            self.libraries = [
                Path(library) / "steamapps"
                for library in re.findall(r'"path"\s+"(\S+)"', libraries_file.read())
            ]
        for library in self.libraries:
            for game in [
                (game.name, library)
                for game in (library / "common").iterdir()
                if game.name in self.ids
            ]:
                self.games.append(game)

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
        for i, (game, _) in enumerate(self.games):
            index = f"[{i}]"
            result += f"{index:<7} {game}\n"
        return result

    def _populate_index_commands(self):
        """
        Hack to get methods named after numbers,
        one for each selectable option.
        """
        for i in range(len(self.games)):
            setattr(self, str(i), lambda self, i=i: self._manage_game(i))
            self.__dict__[str(i)].__doc__ = f"Manage {self.games[i]}"

    def _manage_game(self, index: int):
        """
        Gather paths for the game at <index>. Create an instance of
        ModController for that game, then run it under the UI.
        """
        name, library = self.games[index]

        app_id = self.ids[name]
        pfx = library / f"compatdata/{app_id}/pfx"
        directory = library / f"common/{name}"
        app_data = library / f"{pfx}/drive_c/users/steamuser/AppData/Local"
        dlc_file = app_data / f"{name.replace('t 4', 't4')}/DLCList.txt"
        plugin_file = app_data / f"{name.replace('t 4', 't4')}/Plugins.txt"
        data = directory / "Data"
        ammo_mods_dir = Path.home() / f".local/share/ammo/{name}/mods"
        ammo_conf_dir = Path.home() / f".local/share/ammo/{name}"
        ammo_conf = ammo_conf_dir / "ammo.conf"

        game = Game(
            name,
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