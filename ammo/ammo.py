#!/usr/bin/env python3
import sys
from pathlib import Path
from .ui import UI
from .mod_controller import (
    Game,
    ModController,
)

IDS = {
    "Skyrim Special Edition": "489830",
    "Oblivion": "22330",
    "Fallout 4": "377160",
    "Skyrim": "72850",
    "Enderal": "933480",
    "Enderal Special Edition": "976620",
    "Starfield": "1716740",
}
DOWNLOADS = Path.home() / "Downloads"
STEAM = Path.home() / ".local/share/Steam/steamapps"


def main():
    # game selection
    games = [game.name for game in (STEAM / "common").iterdir() if game.name in IDS]
    if not games:
        print("Install a game through steam!")
        print("ammo supports:")
        for i in IDS:
            print(f"- {i}")
        print(f"ammo looks for games in {STEAM/'common'}")
        print("ammo stores mods in ~/.local/share/ammo")
        print("ammo looks for mods to install in ~/Downloads")
        sys.exit(1)

    if len(games) == 1:
        CHOICE = 0
    else:
        while True:
            CHOICE = None
            print("Index   |   Game")
            print("----------------")
            for index, game in enumerate(games):
                print(f"[{index}]         {game}")
            CHOICE = input("Index of game to manage: ")
            if CHOICE.strip().lower() == "exit":
                exit()
            try:
                CHOICE = int(CHOICE)
                assert CHOICE in range(len(games))
            except ValueError:
                print(f"Expected integer 0 through {len(games) - 1} (inclusive)")
                continue
            except AssertionError:
                print(f"Expected integer 0 through {len(games) - 1} (inclusive)")
                continue
            break

    # Get the paths and files associated with our game.
    name = games[CHOICE]
    app_id = IDS[name]
    pfx = STEAM / f"compatdata/{app_id}/pfx"
    directory = STEAM / f"common/{name}"
    app_data = STEAM / f"{pfx}/drive_c/users/steamuser/AppData/Local"
    dlc_file = app_data / f"{name.replace('t 4', 't4')}/DLCList.txt"
    plugin_file = app_data / f"{name.replace('t 4', 't4')}/Plugins.txt"
    data = directory / "Data"
    ammo_mods_dir = Path.home() / f".local/share/ammo/{name}/mods"
    ammo_conf_dir = Path.home() / f".local/share/ammo/{name}"
    ammo_conf = ammo_conf_dir / "ammo.conf"

    # Create expected directories if they don't alrady exist.
    for expected_dir in [ammo_mods_dir, ammo_conf_dir]:
        Path.mkdir(expected_dir, parents=True, exist_ok=True)

    # Get a ammo_configuration for the chosen game
    game = Game(
        name,
        directory,
        data,
        ammo_conf,
        dlc_file,
        plugin_file,
        ammo_mods_dir,
    )

    # Create an instance of the controller.
    controller = ModController(DOWNLOADS, game)

    # Run the UI against the controller.
    ui = UI(controller)
    return ui.repl()
