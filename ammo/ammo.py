#!/usr/bin/env python3
import os
import sys
from .ui import UI
from .controller import Controller
from .game import Game

IDS = {
    "Skyrim Special Edition": "489830",
    "Oblivion": "22330",
    "Fallout 4": "377160",
    "Skyrim": "72850",
    "Enderal": "933480",
    "Enderal Special Edition": "976620",
}
HOME = os.environ["HOME"]
DOWNLOADS = os.path.join(HOME, "Downloads")
STEAM = os.path.join(HOME, ".local/share/Steam/steamapps")


def main():
    # game selection
    games = [game for game in os.listdir(os.path.join(STEAM, "common")) if game in IDS]
    if not games:
        print("Install a game through steam!")
        print("ammo supports:")
        for i in IDS:
            print(f"- {i}")
        print(f"ammo looks for games in {os.path.join(STEAM, 'common')}")
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
    pfx = os.path.join(STEAM, f"compatdata/{app_id}/pfx")
    directory = os.path.join(STEAM, f"common/{name}")
    app_data = os.path.join(STEAM, f"{pfx}/drive_c/users/steamuser/AppData/Local")
    dlc_file = os.path.join(app_data, f"{name.replace('t 4', 't4')}/DLCList.txt")
    plugin_file = os.path.join(app_data, f"{name.replace('t 4', 't4')}/Plugins.txt")
    data = os.path.join(directory, "Data")
    ammo_mods_dir = os.path.join(HOME, f".local/share/ammo/{name}/mods")
    ammo_conf_dir = os.path.join(HOME, f".local/share/ammo/{name}")
    ammo_conf = os.path.join(ammo_conf_dir, "ammo.ammo_conf")

    # Create expected directories if they don't alrady exist.
    for expected_dir in [ammo_mods_dir, ammo_conf_dir]:
        if not os.path.exists(expected_dir):
            os.makedirs(expected_dir)

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
    controller = Controller(DOWNLOADS, game)

    # Run the UI against the controller.
    ui = UI(controller)
    return ui.repl()
