#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from xml.etree import ElementTree

from ammo.game import Game
from ammo.controller import Controller


# Create a configuration for the mock controller to use.
AMMO_DIR = Path("/tmp/ammo_test")

GAME = Game(
    name="MockGame",
    directory=Path("/tmp/MockGame"),
    data=Path("/tmp/MockGame/Data"),
    ammo_conf=Path(f"{AMMO_DIR}/ammo.conf"),
    dlc_file=Path(f"{AMMO_DIR}/dlcList.txt"),
    plugin_file=Path(f"{AMMO_DIR}/Plugins.txt"),
    ammo_mods_dir=Path(f"{AMMO_DIR}/MockGame/mods"),
)


class AmmoController:
    """
    Context manager for ammo's controller class.

    Builds a Controller instance to run against /tmp/MockGame.
    Ammo's configuration directory will be set up as AMMO_DIR,
    if it doesn't already exist.

    Removes those folders on exit or error.
    """

    def __init__(self):
        self.game = GAME
        script_path = Path(__file__)
        self.downloads_dir = script_path.parent / "Downloads"

    def __enter__(self):
        """
        Return an instance of ammo's controller for tests to
        interact with.
        """
        return Controller(self.downloads_dir, self.game)

    def __exit__(self, *args, **kwargs):
        """
        Remove all the files and folders associated with our mock
        ammo instance. This ensures no reliance on a state
        created by a previous test.
        """
        # remove symlinks
        for dirpath, _dirnames, filenames in os.walk(self.game.directory):
            for file in filenames:
                full_path = Path(dirpath) / file
                if full_path.is_symlink():
                    full_path.unlink()

        # remove empty directories
        def remove_empty_dirs(path):
            print(f"deleting stuff in {path}")
            for dirpath, dirnames, _filenames in list(os.walk(path, topdown=False)):
                for dirname in dirnames:
                    try:
                        Path(dirpath, dirname).rmdir()
                    except OSError:
                        # directory wasn't empty, ignore this
                        pass

        if self.game.directory.exists():
            remove_empty_dirs(self.game.directory)
        if self.game.directory.exists():
            shutil.rmtree(self.game.directory)
        if AMMO_DIR.exists():
            shutil.rmtree(AMMO_DIR)


def mod_extracts_files(mod_name, files):
    """
    Expects the name of a file in Downloads, and a list of file paths that should
    exist, relative to the mod's installation directory.
    """
    with AmmoController() as controller:
        # install the mod
        mod_index_download = [i.name for i in controller.downloads].index(
            mod_name + ".7z"
        )
        controller.install(mod_index_download)

        # Assert the mod extracted to the expected place
        assert mod_name == controller.mods[0].name
        assert (controller.game.ammo_mods_dir / mod_name).exists()

        for file in files:
            expected_file = controller.mods[0].location / file

            if not expected_file.exists():
                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(
                    controller.game.ammo_mods_dir
                ):
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
        mod_index_download = [i.name for i in controller.downloads].index(
            mod_name + ".7z"
        )
        controller.install(mod_index_download)
        mod_index = [i.name for i in controller.mods].index(mod_name)
        controller.activate("mod", mod_index)

        # activate any plugins this mod has
        for plugin in range(len(controller.plugins)):
            controller.activate("plugin", plugin)

        controller.commit()

        for file in files:
            expected_file = controller.game.directory / file
            if not expected_file.exists():
                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(
                    controller.game.directory
                ):
                    print(f"{parent_dir} folders: {folders}")
                    print(f"{parent_dir} files: {actual_files}")

                print(f"expected: {expected_file}")
                raise FileNotFoundError(expected_file)

            if expected_file.is_symlink():
                # Catch any broken symlinks.
                assert (
                    expected_file.readlink().exists()
                ), f"Detected broken symlink: {expected_file}"

            else:
                # Make sure hardlinks have more than 1 st_nlink
                assert (
                    os.stat(expected_file).st_nlink > 1
                ), f"Detected lonely hard link: {expected_file}"


def fomod_selections_choose_files(mod_name, files, selections=[]):
    """
    Configure a fomod with flags, using default flags if unspecified.

    Test that this causes all and only all of 'files' to exist,
    relative to the mod's local data directory.

    selections is a list of {"page": <page_number>, "option": <selection index>}
    """
    with AmmoController() as controller:
        mod_index_download = [i.name for i in controller.downloads].index(
            mod_name + ".7z"
        )
        controller.install(mod_index_download)

        mod_index = [i.name for i in controller.mods].index(mod_name)
        mod = controller.mods[mod_index]
        try:
            shutil.rmtree(mod.location / "Data")
        except FileNotFoundError:
            pass

        tree = ElementTree.parse(mod.modconf)
        xml_root_node = tree.getroot()
        steps = controller._fomod_get_steps(xml_root_node)
        for selection in selections:
            flags = controller._fomod_get_flags(steps)
            visible_pages = controller._fomod_get_pages(steps, flags)
            page = steps[visible_pages[selection["page"]]]
            controller._fomod_select(page, selection["option"])

        flags = controller._fomod_get_flags(steps)
        install_nodes = controller._fomod_get_nodes(xml_root_node, steps, flags)
        controller._fomod_install_files(mod_index, install_nodes)

        # Check that all the expected files exist.
        for file in files:
            expected_file = mod.location / file
            if not expected_file.exists():
                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(mod.location):
                    print(f"{parent_dir} folders: {folders}")
                    print(f"{parent_dir} files: {actual_files}")

                print(f"expected: {expected_file}")
                raise FileNotFoundError(expected_file)

        # Check that no unexpected files exist.
        for path, folders, filenames in os.walk(mod.location / "Data"):
            for file in filenames:
                exists = os.path.join(path, file)
                local_exists = exists.split(str(mod.location))[-1].lstrip("/")
                assert local_exists in [
                    str(i) for i in files
                ], f"Got an extra file: {local_exists}\nExpected only: {files}"


def install_everything(controller):
    """
    Helper function that installs everything from downloads,
    then activates all mods and plugins.
    """
    # install everything
    for download in controller.downloads:
        index = controller.downloads.index(download)
        controller.install(index)

    # activate everything that's not a fomod.
    for mod in controller.mods:
        if not mod.fomod:
            index = controller.mods.index(mod)
            controller.activate("mod", index)

    for plugin in controller.plugins:
        index = controller.plugins.index(plugin)
        controller.activate("plugin", index)

    controller.commit()


def extract_mod(controller, mod_name: str):
    """
    Helper function that installs a mod by name.

    Returns the index the mod inhabits.
    """
    index = [i.name for i in controller.downloads].index(f"{mod_name}.7z")
    controller.install(index)
    try:
        mod_index = [i.name for i in controller.mods].index(mod_name)
        return mod_index
    except ValueError:
        # mod_name was not in the list. Print the list.
        print(f"{mod_name} was not in {[i.name for i in controller.mods]}")


def install_mod(controller, mod_name: str):
    """
    Helper function that installs a normal mod,
    then activates it and all plugins associated with it.

    Returns the index the mod inhabits.
    """
    index = [i.name for i in controller.downloads].index(f"{mod_name}.7z")
    controller.install(index)

    mod_index = [i.name for i in controller.mods].index(mod_name)
    controller.activate("mod", mod_index)

    for plugin in controller.mods[mod_index].plugins:
        plugin_index = [i.name for i in controller.plugins].index(plugin)
        controller.activate("plugin", plugin_index)

    controller.commit()

    return mod_index
