#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

from ammo.mod_controller import (
    ModController,
    Game,
)
from ammo.fomod_controller import FomodController
from ammo.component import Mod


# Create a configuration for the mock controller to use.
AMMO_DIR = Path("/tmp/ammo_test")

GAME = Game(
    name="MockGame",
    directory=Path("/tmp/MockGame"),
    data=Path("/tmp/MockGame/Data"),
    ammo_conf=Path(f"{AMMO_DIR}/ammo.conf"),
    ammo_log=Path(f"{AMMO_DIR}/ammo.log"),
    dlc_file=Path(f"{AMMO_DIR}/dlcList.txt"),
    plugin_file=Path(f"{AMMO_DIR}/Plugins.txt"),
    ammo_mods_dir=Path(f"{AMMO_DIR}/MockGame/mods"),
)


class AmmoController:
    """
    Context manager for ammo's controller class.

    Builds a ModController instance to run against /tmp/MockGame.
    Ammo's configuration directory will be set up as AMMO_DIR,
    if it doesn't already exist.

    Removes those folders on exit or error. Raises AssertionError
    after exit logic if there were broken symlinks.
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
        return ModController(self.downloads_dir, self.game)

    def __exit__(self, *args, **kwargs):
        """
        Remove all the files and folders associated with our mock
        ammo instance. This ensures no reliance on a state
        created by a previous test.
        """
        broken_symlinks = {}
        # remove symlinks
        for dirpath, _dirnames, filenames in os.walk(self.game.directory):
            for file in filenames:
                full_path = Path(dirpath) / file
                if full_path.is_symlink():
                    if (dest := full_path.resolve()).exists() is False:
                        broken_symlinks[str(full_path)] = str(dest)
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

        assert {} == broken_symlinks


class FomodContextManager:
    def __init__(self, mod: Mod):
        self.mod = mod

    def __enter__(self):
        return FomodController(self.mod)

    def __exit__(self, *args, **kwargs):
        pass


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
        controller.do_install(mod_index_download)

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


def expect_files(directory, files) -> None:
    """
    Raise an error if any files are missing or if files
    that weren't provided exist.
    """
    for file in files:
        expected_file = directory / file
        if not expected_file.exists():
            # print the files that _do_ exist to show where things ended up
            for parent_dir, folders, actual_files in os.walk(directory):
                print(f"{parent_dir} folders: {folders}")
                print(f"{parent_dir} files: {actual_files}")

            print(f"expected: {expected_file}")
            raise FileNotFoundError(expected_file)

        # Catch any broken symlinks.
        assert (
            expected_file.readlink().exists()
        ), f"Detected broken symlink: {expected_file}"

    # Check that no unexpected files exist.
    for path, folders, filenames in os.walk(directory):
        for file in filenames:
            exists = os.path.join(path, file)
            local_exists = exists.split(str(directory))[-1].lstrip("/")
            assert (
                local_exists in [str(i) for i in files]
            ), f"Got an extra file: {local_exists}\nExpected only: {[str(i) for i in files]}"


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
        controller.do_install(mod_index_download)
        mod_index = [i.name for i in controller.mods].index(mod_name)
        controller.do_activate_mod(mod_index)

        # activate any plugins this mod has
        for plugin in range(len(controller.plugins)):
            controller.do_activate_plugin(plugin)

        controller.do_commit()
        expect_files(controller.game.directory, files)


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
        controller.do_install(mod_index_download)

        mod_index = [i.name for i in controller.mods].index(mod_name)
        mod = controller.mods[mod_index]
        try:
            shutil.rmtree(mod.location / "ammo_fomod" / "Data")
        except FileNotFoundError:
            pass

        with FomodContextManager(mod) as fomod_controller:
            for selection in selections:
                fomod_controller.page = fomod_controller.steps[
                    fomod_controller.steps.index(
                        fomod_controller.visible_pages[selection["page"]]
                    )
                ]
                fomod_controller.select(selection["option"])

            fomod_controller.flags = fomod_controller.get_flags()
            install_nodes = fomod_controller.get_nodes()
            fomod_controller.install_files(install_nodes)

        # Check that all the expected files exist.
        for file in files:
            expected_file = mod.location / "ammo_fomod" / file
            if not expected_file.exists():
                # print the files that _do_ exist to show where things ended up
                for parent_dir, folders, actual_files in os.walk(
                    mod.location / "ammo_fomod"
                ):
                    print(f"{parent_dir} folders: {folders}")
                    print(f"{parent_dir} files: {actual_files}")

                print(f"expected: {expected_file}")
                raise FileNotFoundError(expected_file)

        # Check that no unexpected files exist.
        for path, folders, filenames in os.walk(mod.location / "ammo_fomod" / "Data"):
            for file in filenames:
                exists = os.path.join(path, file)
                local_exists = exists.split(str(mod.location / "ammo_fomod"))[
                    -1
                ].lstrip("/")
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
        controller.do_install(index)

    # activate everything that's not a fomod.
    for mod in controller.mods:
        if not mod.fomod:
            index = controller.mods.index(mod)
            controller.do_activate_mod(index)

    for plugin in controller.plugins:
        index = controller.plugins.index(plugin)
        controller.do_activate_plugin(index)

    controller.do_commit()


def extract_mod(controller, mod_name: str):
    """
    Helper function that installs a mod by name.

    Returns the index the mod inhabits.
    """
    index = [i.name for i in controller.downloads].index(f"{mod_name}.7z")
    controller.do_install(index)
    try:
        mod_index = [i.name for i in controller.mods].index(mod_name)
        return mod_index
    except ValueError:
        # mod_name was not in the list. Print the list.
        print(f"{mod_name} was not in {[i.name for i in controller.mods]}")


def install_mod(controller, mod_name: str):
    """
    Helper function that installs a normal mod, then activates it and all
    plugins associated with it.

    Returns the index the mod inhabits.
    """
    index = [i.name for i in controller.downloads].index(f"{mod_name}.7z")
    controller.do_install(index)

    mod_index = [i.name for i in controller.mods].index(mod_name)
    controller.do_activate_mod(mod_index)

    for plugin in controller.mods[mod_index].plugins:
        plugin_index = [i.name for i in controller.plugins].index(plugin.name)
        controller.do_activate_plugin(plugin_index)

    controller.do_commit()
    assert controller.mods[mod_index].enabled is True
    for plugin in controller.mods[mod_index].plugins:
        plugin_index = [i.name for i in controller.plugins].index(plugin.name)
        assert controller.plugins[plugin_index].enabled is True

    return mod_index
