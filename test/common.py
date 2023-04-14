#!/usr/bin/env python3
import os
import sys
import shutil

sys.path.append(os.path.abspath("../ammo"))
from controller import Controller


class AmmoController:
    """
    Builds a Controller instance to run against /tmp/MockGame.
    Safely deletes /tmp/MockGame on exit.
    """

    def __init__(self):
        self.app_name = "MockGame"
        self.game_dir = "/tmp/MockGame"
        self.dlc = "/tmp/ammo_test/dlcList.txt"
        self.data = "/tmp/MockGame/Data"
        self.ammo_dir = "/tmp/ammo_test"
        self.conf = "/tmp/ammo_test/ammo.conf"
        self.plugins = "/tmp/ammo_test/Plugins.txt"
        self.mods_dir = "/tmp/ammo_test/MockGame/mods"
        self.downloads = os.path.abspath("./Downloads")

    def __enter__(self):
        assert not os.path.exists(
            self.game_dir
        ), f"{self.game_dir} exists, expected to have to create it!"
        assert not os.path.exists(
            self.ammo_dir
        ), f"{self.ammo_dir} exists, expected to have to create it!"
        return Controller(
            self.app_name,
            self.game_dir,
            self.data,
            self.conf,
            self.dlc,
            self.plugins,
            self.mods_dir,
            self.downloads,
        )

    def __exit__(self, *args, **kwargs):
        # remove symlinks
        for dirpath, _dirnames, filenames in os.walk(self.game_dir):
            for file in filenames:
                full_path = os.path.join(dirpath, file)
                if os.path.islink(full_path):
                    os.unlink(full_path)

        # remove empty directories
        def remove_empty_dirs(path):
            for dirpath, dirnames, _filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    try:
                        os.rmdir(os.path.realpath(os.path.join(dirpath, dirname)))
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        remove_empty_dirs(self.game_dir)
        shutil.rmtree(self.game_dir)
        shutil.rmtree(self.ammo_dir)
