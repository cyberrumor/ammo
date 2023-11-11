#!/usr/bin/env python3
import os
import pytest
from ammo.component import (
    ComponentEnum,
    DeleteEnum,
)
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
        controller.move(ComponentEnum("mod"), 0, highest)
        controller.move(ComponentEnum("mod"), highest, 0)

        # Test valid move plugin input
        highest = len(controller.plugins) - 1
        controller.move(ComponentEnum("plugin"), 0, highest)
        controller.move(ComponentEnum("plugin"), highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on mods.
        highest = len(controller.mods)
        controller.move(ComponentEnum("mod"), 0, highest)

        # Test invalid 'from index' for mods.
        with pytest.raises(Warning):
            controller.move(ComponentEnum("mod"), highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on plugins.
        highest = len(controller.plugins)
        controller.move(ComponentEnum("plugin"), 0, highest)

        # Test invalid 'from index' for plugins.
        with pytest.raises(Warning):
            controller.move(ComponentEnum("plugin"), highest, 0)

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
        controller.activate(ComponentEnum("mod"), mod_index)

        plugin_index = [i.name for i in controller.plugins].index("normal_plugin.esp")

        # Activate valid plugin
        controller.activate(ComponentEnum("plugin"), plugin_index)

        # Activate invalid mod
        with pytest.raises(Warning):
            controller.activate(ComponentEnum("mod"), 1000)

        # Activate invalid plugin
        with pytest.raises(Warning):
            controller.activate(ComponentEnum("plugin"), 1000)

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
        controller.deactivate(ComponentEnum("plugin"), plugin_index)

        # valid deactivate mod
        controller.deactivate(ComponentEnum("mod"), mod_index)

        # invalid deactivate plugin.
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum("plugin"), plugin_index)

        # invalid deactivate mod
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum("mod"), 1000)

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
            controller.delete(DeleteEnum("mod"), 1000)

        # delete mod in range
        with pytest.raises(Warning):
            controller.delete(DeleteEnum("mod"), 0)

        # delete download out of range
        with pytest.raises(Warning):
            controller.delete(DeleteEnum("download"), 1000)

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
        controller.delete(DeleteEnum("download"), download_index)


def test_no_components_validation():
    """
    In the absence of any mods, plugins, or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod/plugin
        with pytest.raises(Warning):
            controller.move(ComponentEnum("mod"), 0, 1)
        with pytest.raises(Warning):
            controller.move(ComponentEnum("plugin"), 0, 1)

        # attempt to delete mod
        with pytest.raises(Warning):
            controller.delete(DeleteEnum("mod"), 0)

        # attempt to activate mod/plugin
        with pytest.raises(Warning):
            controller.activate(ComponentEnum("mod"), 0)
        with pytest.raises(Warning):
            controller.activate(ComponentEnum("plugin"), 0)

        # attempt to deactivate mod/plugin
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum("mod"), 0)
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum("plugin"), 0)


def test_no_install_twice():
    """
    Attempting to install a mod that is already installed isn't supported.
    Explicitly test that this is not allowed.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        with pytest.raises(Warning):
            install_mod(controller, "normal_mod")
