#!/usr/bin/env python3
import os
from common import (
    AmmoController,
    install_everything,
    install_normal_mod_active,
    install_normal_mod_inactive,
)


def test_move_validation():
    """
    Install several mods, then check various arguments to "move" for validity.
    """
    with AmmoController() as controller:
        install_everything(controller)

        # Test valid move mod input
        highest = len(controller.mods) - 1
        assert (
            controller.move("mod", 0, highest) is True
        ), "valid input was considered an error"
        assert (
            controller.move("mod", highest, 0) is True
        ), "valid input was considered an error"

        # Test valid move plugin input
        highest = len(controller.plugins) - 1
        assert (
            controller.move("plugin", 0, highest) is True
        ), "valid input was considered an error"
        assert (
            controller.move("plugin", highest, 0) is True
        ), "valid input was considered an error"

        # Test invalid move mod input
        highest = len(controller.mods)
        assert (
            controller.move("mod", 0, highest) is False
        ), "issue moving mod to outside of range"
        assert (
            controller.move("mod", highest, 0) is False
        ), "issue moving mod from outside of range"

        # Test invalid move plugin input
        highest = len(controller.plugins)
        assert (
            controller.move("plugin", 0, highest) is False
        ), "issue moving plugin to outside of range"
        assert (
            controller.move("plugin", highest, 0) is False
        ), "issue moving plugin from outside of range"

        # Test invalid move component type
        assert (
            controller.move("download", 0, 1) is False
        ), "issue while attempting to move a download"


def test_activate_validation():
    """
    Install a mod, then check various arguments to "activate" for validity
    """
    with AmmoController() as controller:
        mod_index = install_normal_mod_inactive(controller)

        # Activate valid mod
        assert (
            controller.activate("mod", mod_index) is True
        ), "valid input was considered an error"

        plugin_index = [i.name for i in controller.plugins].index("normal_plugin.esp")

        # Activate valid plugin
        assert (
            controller.activate("plugin", plugin_index) is True
        ), "valid input was considered an error"

        # Activate invalid mod
        assert (
            controller.activate("mod", 1000) is False
        ), "issue attempting to activate mod out of range"

        # Activate invalid plugin
        assert (
            controller.activate("plugin", 1000) is False
        ), "issue attempting to activate plugin out of range"


def test_deactivate_validation():
    """
    Install a mod, then check various arguments to "deactivate" for validity
    """
    with AmmoController() as controller:
        mod_index, plugin_index = install_normal_mod_active(controller)

        # valid deactivate plugin
        assert (
            controller.deactivate("plugin", plugin_index) is True
        ), "valid input was considered invalid"

        # valid deactivate mod
        assert (
            controller.deactivate("mod", mod_index) is True
        ), "valid input was considered an error"

        # invalid deactivate plugin.
        assert (
            controller.deactivate("plugin", plugin_index) is False
        ), "valid input was considered invalid, did the plugin fail to disappear?"

        # invalid deactivate mod
        assert (
            controller.deactivate("mod", 1000) is False
        ), "issue attempting to deactivate mod out of range"


def test_install_validation():
    """
    Attempt to install a valid and invalid index.
    """
    with AmmoController() as controller:
        assert controller.install(0) is True, "valid input was considered an error"

        assert (
            controller.install(1000) is False
        ), "issue attempting to install mod out of range"


def test_delete_validation():
    """
    Delete a valid and invalid mod and download
    """
    with AmmoController() as controller:
        install_normal_mod_active(controller)

        # delete mod out of range
        assert controller.delete("mod", 1) is False, "issue deleting mod out of range"

        # delete mod in range
        assert (
            controller.delete("mod", 0) is True
        ), "valid input was considered an error"

        # delete download out of range
        assert (
            controller.delete("download", 1000) is False
        ), "issue deleting download out of range"

        # generate an expendable download file
        with open(os.path.join(controller.downloads_dir, "temp_download.7z"), "w") as f:
            f.write("zzz")

        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )
        assert (
            controller.delete("download", download_index) is True
        ), "valid input was considered an error"


def test_no_components_validation():
    """
    In the absence of any mods, plugins, or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod/plugin
        assert (
            controller.move("mod", 0, 1) is False
        ), "issue while attempting to move mod when there are no components"
        assert (
            controller.move("plugin", 0, 1) is False
        ), "issue while attempting to move plugin when there are no components"

        # attempt to delete mod
        assert (
            controller.delete("mod", 0) is False
        ), "issue while attempting to delete a mod when there are no components"

        # attempt to activate mod/plugin
        assert (
            controller.activate("mod", 0) is False
        ), "issue while attempting to activate a mod when there are no components"
        assert (
            controller.activate("plugin", 0) is False
        ), "issue while attempting to activate a plugin when there are no components"

        # attempt to deactivate mod/plugin
        assert (
            controller.deactivate("mod", 0) is False
        ), "issue while attempting to deactivate a mod when there are no components"
        assert (
            controller.deactivate("plugin", 0) is False
        ), "issue while attempting to deactivate a plugin when there are no components"

        # attempt to configure a non-existing mod
        assert (
            controller._fomod_get_root_node(0) is False
        ), "issue while attempting to configure a mod when there are no components"
