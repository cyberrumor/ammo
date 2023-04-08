#!/usr/bin/env python3
import os
import sys
from ui import UI
from controller import Controller

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

if __name__ == "__main__":
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

    # create the paths
    app_name = games[CHOICE]
    app_id = IDS[app_name]
    pfx = os.path.join(STEAM, f"compatdata/{app_id}/pfx")
    game_dir = os.path.join(STEAM, f"common/{app_name}")
    app_data = os.path.join(STEAM, f"{pfx}/drive_c/users/steamuser/AppData/Local")
    plugins = os.path.join(app_data, f"{app_name.replace('t 4', 't4')}/Plugins.txt")
    dlc = os.path.join(app_data, f"{app_name.replace('t 4', 't4')}/DLCList.txt")

    data = os.path.join(game_dir, "Data")
    mods_dir = os.path.join(HOME, f".local/share/ammo/{app_name}/mods")
    conf_dir = os.path.join(HOME, f".local/share/ammo/{app_name}")
    conf = os.path.join(conf_dir, "ammo.conf")

    # Create expected directories if they don't alrady exist.
    for expected_dir in [mods_dir, conf_dir]:
        if not os.path.exists(expected_dir):
            os.makedirs(expected_dir)

    # Create an instance of the controller.
    controller = Controller(
        app_name, game_dir, data, conf, dlc, plugins, mods_dir, DOWNLOADS
    )
    # Run the UI against the controller.
    ui = UI(controller)
    sys.exit(ui.repl())
