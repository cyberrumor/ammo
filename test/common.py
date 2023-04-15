#!/usr/bin/env python3
import os
import sys
import shutil

sys.path.append(os.path.abspath("../ammo"))
from controller import Controller


class AmmoController:
    """
    Context manager for ammo's controller class.

    Builds a Controller instance to run against /tmp/MockGame.
    Ammo's configuration directory will be set up as /tmp/ammo_test.

    Requires absence of those folders on start.

    Removes those folders on exit or error.
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
        """
        Verify clean state by requiring the absence of folders
        that would only exist if ammo had been run before.

        Then return an instance of ammo's controller for tests to
        interact with.
        """
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
        """
        Remove all the files and folders associated with our mock
        ammo instance. This ensures no reliance on a state
        created by a previous test.
        """
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


def mod_extracts_files(mod_name, files):
    """
    Expects the name of a file in Downloads, and a list of file paths that should
    exist, relative to the mod's installation directory.
    """
    with AmmoController() as controller:
        # install the mod
        mod_index_download = [i.name for i in controller.downloads].index(mod_name)
        controller.install(mod_index_download)

        # Assert the mod extracted to the expected place
        extracted_mod_name = mod_name.strip(".7z")
        assert extracted_mod_name == controller.mods[0].name
        assert os.path.exists(os.path.join(controller.mods_dir, extracted_mod_name))

        for file in files:
            expected_file = os.path.join(controller.mods[0].location, file)

            if not os.path.exists(expected_file):
                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(controller.mod_dir):
                    print(f"{parent_dir} folders: {folders}")
                    print(f"{parent_dir} files: {actual_files}")

                print(f"expected: {expected_file}")

                raise FileNotFoundError(expected_file)


def mod_installs_files(mod_name, files):
    """
    Expects the name of a file in Downloads, and a list of file paths that should
    exist after installation and commit, relative to the game's directory.
    """
    with AmmoController() as controller:
        # install the mod
        mod_index_download = [i.name for i in controller.downloads].index(mod_name)
        controller.install(mod_index_download)

        controller.activate("mod", 0)

        # activate any plugins this mod has
        for plugin in range(len(controller.plugins)):
            controller.activate("plugin", plugin)

        controller.commit()

        for file in files:
            expected_file = os.path.join(controller.game_dir, file)
            if not os.path.exists(expected_file):

                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(controller.game_dir):
                    print(f"{parent_dir} folders: {folders}")
                    print(f"{parent_dir} files: {actual_files}")

                print(f"expected: {expected_file}")

                raise FileNotFoundError(expected_file)

            # Catch any broken symlinks.
            assert os.path.exists(os.readlink(expected_file)), \
                f"Detected broken symlink: {expected_file}"
