#!/usr/bin/env python3
import json
import re
from typing import Union
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from .mod_controller import (
    Game,
    ModController,
)
from .bethesda_controller import (
    BethesdaController,
    BethesdaGame,
)
from .ui import (
    Controller,
    UI,
)


@dataclass(frozen=True, kw_only=True)
class GameSelection:
    name: field(default_factory=str)
    directory: field(default_factory=Path)

    def __post_init__(self):
        """
        Validate that all paths are absolute.
        """
        assert self.directory.is_absolute()


@dataclass(frozen=True, kw_only=True)
class BethesdaGameSelection(GameSelection):
    data: field(default_factory=Path)
    dlc_file: field(default_factory=Path)
    plugin_file: field(default_factory=Path)

    def __post_init__(self):
        """
        Validate that all paths are absolute.
        """
        assert self.data.is_absolute()
        assert self.dlc_file.is_absolute()
        assert self.plugin_file.is_absolute()


class GameController(Controller):
    """
    GameController is responsible for selecting games.
    If there is only one valid game, it is selected automatically,
    in which case users won't see this menu.

    Once a game is selected, GameController launches ModController
    with the selected game and runs it under the UI.
    """

    def __init__(self, args):
        self.args = args
        self.ids = {
            "Skyrim Special Edition": "489830",
            "Oblivion": "22330",
            "Fallout 4": "377160",
            "Skyrim": "72850",
            "Enderal": "933480",
            "Enderal Special Edition": "976620",
            "Starfield": "1716740",
            "Fallout New Vegas": "22380",
        }
        self.downloads = self.args.downloads.resolve(strict=True)
        self.games: list[GameSelection | BethesdaGameSelection] = []

        # Find games from instances of Steam
        self.libraries: list[Path] = []
        self.steam = Path.home() / ".local/share/Steam/steamapps"
        self.flatpak = (
            Path.home()
            / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps"
        )
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

                    pfx = library / f"compatdata/{self.ids[game.name]}/pfx"
                    app_data = pfx / "drive_c/users/steamuser/AppData/Local"

                    game_selection = GameSelection(
                        name=game.name,
                        directory=library / f"common/{game.name}",
                    )

                    if Path(library / f"common/{game.name}/Data").exists():
                        # If there is a data dir, it's a bethesda game.
                        game_selection = BethesdaGameSelection(
                            name=game.name,
                            directory=library / f"common/{game.name}",
                            data=library / f"common/{game.name}/Data",
                            dlc_file=app_data
                            / f"{game.name.replace('t 4', 't4')}/DLCList.txt",
                            plugin_file=app_data
                            / f"{game.name.replace('t 4', 't4')}/Plugins.txt",
                        )

                    self.games.append(game_selection)

        # Find manually configured games
        if args.conf.exists():
            for i in args.conf.iterdir():
                if i.is_file() and i.suffix == ".json":
                    with open(i, "r") as file:
                        j = json.loads(file.read())

                    game_selection = GameSelection(
                        name=i.stem,
                        directory=Path(j["directory"]),
                    )

                    if "data" in j:
                        # If there is a data dir, it's a bethesda game.
                        game_selection = BethesdaGameSelection(
                            name=i.stem,
                            directory=Path(j["directory"]),
                            data=Path(j["data"]),
                            dlc_file=Path(j["dlc_file"]),
                            plugin_file=Path(j["plugin_file"]),
                        )

                    if game_selection not in self.games:
                        self.games.append(game_selection)

        if len(self.games) == 0:
            raise FileNotFoundError(
                f"Supported games {list(self.ids)} not found in {self.libraries}"
            )
        elif len(self.games) == 1:
            self.manage_game(0)
        else:
            self.populate_index_commands()

    def prompt(self) -> str:
        return super().prompt()

    def postcmd(self) -> bool:
        # When we're done managing a game, just quit.
        return True

    def __str__(self) -> str:
        result = ""
        result += " index | Game\n"
        result += "-------|-----\n"
        for i, game in enumerate(self.games):
            index = f"[{i}]"
            result += f"{index:<7} {game.name} ({game.directory})\n"
        return result

    def autocomplete(self, text: str, state: int) -> Union[str, None]:
        return super().autocomplete(text, state)

    def populate_index_commands(self) -> None:
        """
        Hack to get methods named after numbers,
        one for each selectable option.
        """
        for i, game in enumerate(self.games):
            setattr(self, f"do_{i}", lambda _, i=i: self.manage_game(i))
            full_location = str(game.directory).replace(str(Path.home()), "~", 1)
            self.__dict__[f"do_{i}"].__doc__ = full_location

    def manage_game(self, index: int) -> None:
        """
        Gather paths for the game at <index>. Create an instance of
        ModController for that game, then run it under the UI.
        """
        game_selection = self.games[index]

        ammo_conf_dir = self.args.conf.resolve() / game_selection.name
        ammo_mods_dir = (self.args.mods or ammo_conf_dir / "mods").resolve()
        ammo_conf = ammo_conf_dir / "ammo.conf"
        ammo_log = ammo_conf_dir / "ammo.log"

        match game_selection:
            case BethesdaGameSelection():
                match game_selection.name:
                    # Some games expect plugins to be disabled if they begin with
                    # something besides the name, like an asterisk. Other games
                    # use asterisk to denote an enabled plugin.
                    case "Skyrim":

                        def enabled_formula(line) -> bool:
                            return not line.strip().startswith("*")

                    case _:

                        def enabled_formula(line) -> bool:
                            return line.strip().startswith("*")

                game = BethesdaGame(
                    # Generic attributes
                    ammo_conf=ammo_conf,
                    ammo_log=ammo_log,
                    ammo_mods_dir=ammo_mods_dir,
                    name=game_selection.name,
                    directory=game_selection.directory,
                    # Bethesda attributes
                    data=game_selection.data,
                    dlc_file=game_selection.dlc_file,
                    plugin_file=game_selection.plugin_file,
                    enabled_formula=enabled_formula,
                )
                controller_class = BethesdaController

            case GameSelection():
                game = Game(
                    ammo_conf=ammo_conf,
                    ammo_log=ammo_log,
                    ammo_mods_dir=ammo_mods_dir,
                    name=game_selection.name,
                    directory=game_selection.directory,
                )
                controller_class = ModController

        # Launch the appropriate mod organizer.
        controller = controller_class(self.downloads, game)
        ui = UI(controller)
        ui.repl()
