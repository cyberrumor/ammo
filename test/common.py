#!/usr/bin/env python3
import os
import sys
import shutil
from xml.etree import ElementTree

sys.path.append(os.path.abspath("../ammo"))
from controller import Controller


class AmmoController:
    """
    Context manager for ammo's controller class.

    Builds a Controller instance to run against /tmp/MockGame.
    Ammo's configuration directory will be set up as /tmp/ammo_test,
    if it doesn't already exist.

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
        Return an instance of ammo's controller for tests to
        interact with.
        """
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

        if os.path.exists(self.game_dir):
            remove_empty_dirs(self.game_dir)
        if os.path.exists(self.game_dir):
            shutil.rmtree(self.game_dir)
        if os.path.exists(self.ammo_dir):
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
                for parent_dir, folders, actual_files in os.walk(controller.mods_dir):
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
            assert os.path.exists(
                os.readlink(expected_file)
            ), f"Detected broken symlink: {expected_file}"


def install_everything(controller):
    """
    Helper function that installs everything from downloads,
    then activates all mods and plugins.
    """
    # install everything
    for download in controller.downloads:
        index = controller.downloads.index(download)
        controller.install(index)

    # activate everything
    for mod in controller.mods:
        if not mod.fomod:
            index = controller.mods.index(mod)
            assert(
                controller.activate("mod", index) is True
            ), "Unable to activate a mod"


    for plugin in controller.plugins:
        index = controller.plugins.index(plugin)
        controller.activate("plugin", index)

    controller.commit()


def extract_mod(controller, mod_name):
    """
    Helper function that installs a mod by name.

    Returns the index the mod inhabits.
    """
    index = [i.name for i in controller.downloads].index(f"{mod_name}.7z")
    controller.install(index)
    mod_index = [i.name for i in controller.mods].index(mod_name)
    return mod_index


def install_mod(controller, mod_name):
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


def fomod_configures_files(controller, mod_index, files):
    """
    Helper function that configures a fomod with default options.
    """
    controller.deactivate("mod", mod_index)
    controller.commit()
    controller.refresh()
    mod = controller.mods[mod_index]
    try:
        shutil.rmtree(os.path.join(mod.location, "Data"))
    except FileNotFoundError:
        pass
    tree = ElementTree.parse(mod.modconf)
    xml_root_node = tree.getroot()
    steps = controller._fomod_get_steps(xml_root_node)
    flags = controller._fomod_get_flags(steps)
    _visible_pages = controller._fomod_get_pages(steps, flags)

    install_nodes = controller._fomod_get_nodes(xml_root_node, steps, flags)
    controller._fomod_install_files(mod_index, install_nodes)
    controller.refresh()
