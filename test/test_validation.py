#!/usr/bin/env python3
import os
import pytest

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
        with pytest.raises(IndexError):
            controller.move("mod", 0, highest)

        with pytest.raises(IndexError):
            controller.move("mod", highest, 0)

        # Test invalid move plugin input
        highest = len(controller.plugins)
        with pytest.raises(IndexError):
            controller.move("plugin", 0, highest)

        with pytest.raises(IndexError):
            controller.move("plugin", highest, 0)

        # Test invalid move component type
        with pytest.raises(TypeError):
            controller.move("download", 0, 1)


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
        with pytest.raises(IndexError):
            controller.activate("mod", 1000)

        # Activate invalid plugin
        with pytest.raises(IndexError):
            controller.activate("plugin", 1000)

        # Activate invalid component type
        with pytest.raises(TypeError):
            controller.activate("download", 0)


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
        with pytest.raises(IndexError):
            controller.deactivate("plugin", plugin_index)

        # invalid deactivate mod
        with pytest.raises(IndexError):
            controller.deactivate("mod", 1000)

        # Deactivate invalid component type
        with pytest.raises(TypeError):
            controller.deactivate("download", 0)


def test_install_validation():
    """
    Attempt to install a valid and invalid index.
    """
    with AmmoController() as controller:
        assert controller.install(0) is True, "valid input was considered an error"

        with pytest.raises(IndexError):
            controller.install(1000)


def test_delete_validation():
    """
    Delete a valid and invalid mod and download
    """
    with AmmoController() as controller:
        install_normal_mod_active(controller)

        # delete mod out of range
        with pytest.raises(IndexError):
            controller.delete("mod", 1000)

        # delete mod in range
        assert (
            controller.delete("mod", 0) is True
        ), "valid input was considered an error"

        # delete download out of range
        with pytest.raises(IndexError):
            controller.delete("download", 1000)


        # Delete invalid component type
        with pytest.raises(TypeError):
            controller.delete("plugin", 0)

        # generate an expendable download file
        with open(os.path.join(controller.downloads_dir, "temp_download.7z"), "w") as f:
            f.write("")

        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )
        assert (
            controller.delete("download", download_index) is True
        ), "valid input was considered an error"


def test_configure_validation():
    """
    Tests running configure against invalid fomods.
    """
    # TODO: The configure function uniquely has an input loop.
    # Tests should be created for bad input, but they must be configured
    # with a timeout so pytest doesn't hang on that loop.
    pass


def test_no_components_validation():
    """
    In the absence of any mods, plugins, or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod/plugin
        with pytest.raises(IndexError):
            controller.move("mod", 0, 1)
        with pytest.raises(IndexError):
            controller.move("plugin", 0, 1)

        # attempt to delete mod
        with pytest.raises(IndexError):
            controller.delete("mod", 0)

        # attempt to activate mod/plugin
        with pytest.raises(IndexError):
            controller.activate("mod", 0)
        with pytest.raises(IndexError):
            controller.activate("plugin", 0)

        # attempt to deactivate mod/plugin
        with pytest.raises(IndexError):
            controller.deactivate("mod", 0)
        with pytest.raises(IndexError):
            controller.deactivate("plugin", 0)

        # attempt to configure a non-existing mod
        with pytest.raises(IndexError):
            controller._fomod_get_root_node(0)
