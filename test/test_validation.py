#!/usr/bin/env python3
import os
import pytest

from common import (
    AmmoController,
    install_everything,
    install_mod,
    extract_mod,
)


def test_move_validation():
    """
    Install several mods, then check various arguments to "move" for validity.
    """
    with AmmoController() as controller:
        install_everything(controller)

        # Test valid move mod input
        highest = len(controller.mods) - 1
        controller.move("mod", 0, highest)
        controller.move("mod", highest, 0)

        # Test valid move plugin input
        highest = len(controller.plugins) - 1
        controller.move("plugin", 0, highest)
        controller.move("plugin", highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on mods.
        highest = len(controller.mods)
        controller.move("mod", 0, highest)

        # Test invalid 'from index' for mods.
        with pytest.raises(Warning):
            controller.move("mod", highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on plugins.
        highest = len(controller.plugins)
        controller.move("plugin", 0, highest)

        # Test invalid 'from index' for plugins.
        with pytest.raises(Warning):
            controller.move("plugin", highest, 0)

        # Test invalid move component type
        with pytest.raises(Warning):
            controller.move("download", 0, 1)


def test_activate_validation():
    """
    Install a mod, then check various arguments to "activate" for validity
    """
    with AmmoController() as controller:
        mod_index = extract_mod(controller, "normal_mod")

        # Activate valid mod
        controller.activate("mod", mod_index)

        plugin_index = [i.name for i in controller.plugins].index("normal_plugin.esp")

        # Activate valid plugin
        controller.activate("plugin", plugin_index)

        # Activate invalid mod
        with pytest.raises(Warning):
            controller.activate("mod", 1000)

        # Activate invalid plugin
        with pytest.raises(Warning):
            controller.activate("plugin", 1000)

        # Activate invalid component type
        with pytest.raises(Warning):
            controller.activate("download", 0)


def test_deactivate_validation():
    """
    Install a mod, then check various arguments to "deactivate" for validity
    """
    with AmmoController() as controller:
        mod_index = install_mod(controller, "normal_mod")
        plugin_index = [i.name for i in controller.plugins].index(
            controller.mods[mod_index].plugins[0]
        )

        # valid deactivate plugin
        controller.deactivate("plugin", plugin_index)

        # valid deactivate mod
        controller.deactivate("mod", mod_index)

        # invalid deactivate plugin.
        with pytest.raises(Warning):
            controller.deactivate("plugin", plugin_index)

        # invalid deactivate mod
        with pytest.raises(Warning):
            controller.deactivate("mod", 1000)

        # Deactivate invalid component type
        with pytest.raises(Warning):
            controller.deactivate("download", 0)


def test_install_validation():
    """
    Attempt to install a valid and invalid index.
    """
    with AmmoController() as controller:
        controller.install(0)

        with pytest.raises(Warning):
            controller.install(1000)


def test_delete_validation():
    """
    Delete a valid and invalid mod and download
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        # delete mod out of range
        with pytest.raises(Warning):
            controller.delete("mod", 1000)

        # delete mod in range
        controller.delete("mod", 0)

        # delete download out of range
        with pytest.raises(Warning):
            controller.delete("download", 1000)

        # Delete invalid component type
        with pytest.raises(Warning):
            controller.delete("plugin", 0)

        # generate an expendable download file
        with open(os.path.join(controller.downloads_dir, "temp_download.7z"), "w") as f:
            f.write("")

        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )
        controller.delete("download", download_index)


def test_no_components_validation():
    """
    In the absence of any mods, plugins, or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod/plugin
        with pytest.raises(Warning):
            controller.move("mod", 0, 1)
        with pytest.raises(Warning):
            controller.move("plugin", 0, 1)

        # attempt to delete mod
        with pytest.raises(Warning):
            controller.delete("mod", 0)

        # attempt to activate mod/plugin
        with pytest.raises(Warning):
            controller.activate("mod", 0)
        with pytest.raises(Warning):
            controller.activate("plugin", 0)

        # attempt to deactivate mod/plugin
        with pytest.raises(Warning):
            controller.deactivate("mod", 0)
        with pytest.raises(Warning):
            controller.deactivate("plugin", 0)


def test_no_install_twice():
    """
    Attempting to install a mod that is already installed isn't supported.
    Explicitly test that this is not allowed.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        with pytest.raises(Warning):
            install_mod(controller, "normal_mod")
