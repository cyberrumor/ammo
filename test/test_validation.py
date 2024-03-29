#!/usr/bin/env python3
import os
import pytest
from ammo.component import (
    ComponentEnum,
    DeleteEnum,
    RenameEnum,
)
from common import (
    AmmoController,
    install_mod,
    extract_mod,
)


def test_move_validation():
    """
    Install several mods, then check various arguments to "move" for validity.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "multiple_plugins")

        # Test valid move mod input
        highest = len(controller.mods) - 1
        controller.move(ComponentEnum.MOD, 0, highest)
        controller.move(ComponentEnum.MOD, highest, 0)

        # Test valid move plugin input
        highest = len(controller.plugins) - 1
        controller.move(ComponentEnum.PLUGIN, 0, highest)
        controller.move(ComponentEnum.PLUGIN, highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on mods.
        highest = len(controller.mods)
        controller.move(ComponentEnum.MOD, 0, highest)

        # Test invalid 'from index' for mods.
        with pytest.raises(Warning):
            controller.move(ComponentEnum.MOD, highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on plugins.
        highest = len(controller.plugins)
        controller.move(ComponentEnum.PLUGIN, 0, highest)

        # Test invalid 'from index' for plugins.
        with pytest.raises(Warning):
            controller.move(ComponentEnum.PLUGIN, highest, 0)

        # Test invalid move component type
        with pytest.raises(TypeError):
            controller.move(DeleteEnum.DOWNLOAD, 0, 1)

        with pytest.raises(TypeError):
            controller.move(DeleteEnum.MOD, 0, 1)

        with pytest.raises(TypeError):
            controller.move("bogus string", 0, 1)


def test_activate_validation():
    """
    Install a mod, then check various arguments to "activate" for validity
    """
    with AmmoController() as controller:
        mod_index = extract_mod(controller, "normal_mod")

        # Activate valid mod
        controller.activate(ComponentEnum.MOD, mod_index)

        plugin_index = [i.name for i in controller.plugins].index("normal_plugin.esp")

        # Activate valid plugin
        controller.activate(ComponentEnum.PLUGIN, plugin_index)

        # Activate invalid mod
        with pytest.raises(Warning):
            controller.activate(ComponentEnum.MOD, 1000)

        # Activate invalid plugin
        with pytest.raises(Warning):
            controller.activate(ComponentEnum.PLUGIN, 1000)

        # Activate invalid component type
        with pytest.raises(TypeError):
            controller.activate(DeleteEnum.DOWNLOAD, 0)

        with pytest.raises(TypeError):
            controller.activate(DeleteEnum.MOD, 0)

        with pytest.raises(TypeError):
            controller.activate("bogus string", 0)


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
        controller.deactivate(ComponentEnum.PLUGIN, plugin_index)

        # valid deactivate mod
        controller.deactivate(ComponentEnum.MOD, mod_index)

        # invalid deactivate plugin.
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum.PLUGIN, plugin_index)

        # invalid deactivate mod
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum.MOD, 1000)

        # Deactivate invalid component type
        with pytest.raises(TypeError):
            controller.deactivate(DeleteEnum.DOWNLOAD, 0)

        with pytest.raises(TypeError):
            controller.deactivate("bogus string", 0)


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
    Delete a valid and invalid mod, plugin and download
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        # delete plugin out of range
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.PLUGIN, 1000)

        # delete plugin in range
        controller.delete(DeleteEnum.PLUGIN, 0)

        # delete mod out of range
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.MOD, 1000)

        # delete mod in range
        controller.delete(DeleteEnum.MOD, 0)

        # delete download out of range
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.DOWNLOAD, 1000)

        # Delete invalid component type
        with pytest.raises(TypeError):
            controller.delete(ComponentEnum.PLUGIN, 0)

        with pytest.raises(TypeError):
            controller.delete("bogus string", 0)

        # generate an expendable download file, delete
        # download in range.
        with open(os.path.join(controller.downloads_dir, "temp_download.7z"), "w") as f:
            f.write("")

        controller.refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )
        controller.delete(DeleteEnum.DOWNLOAD, download_index)


def test_no_components_validation():
    """
    In the absence of any mods, plugins, or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod/plugin
        with pytest.raises(Warning):
            controller.move(ComponentEnum.MOD, 0, 1)
        with pytest.raises(Warning):
            controller.move(ComponentEnum.PLUGIN, 0, 1)

        # attempt to delete mod / plugin
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.MOD, 0)
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.PLUGIN, 0)

        # attempt to activate mod/plugin
        with pytest.raises(Warning):
            controller.activate(ComponentEnum.MOD, 0)
        with pytest.raises(Warning):
            controller.activate(ComponentEnum.PLUGIN, 0)

        # attempt to deactivate mod/plugin
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum.MOD, 0)
        with pytest.raises(Warning):
            controller.deactivate(ComponentEnum.PLUGIN, 0)


def test_no_install_twice():
    """
    Attempting to install a mod that is already installed isn't supported.
    Explicitly test that this is not allowed.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        with pytest.raises(Warning):
            install_mod(controller, "normal_mod")


def test_invisible_install():
    """
    Don't allow installing hidden downloads.
    """
    with AmmoController() as controller:
        controller.find("nothing")

        with pytest.raises(Warning):
            controller.install(0)


def test_invisible_delete_mod():
    """
    Don't allow deleting hidden mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.delete(DeleteEnum.MOD, 0)


def test_invisible_delete_plugin():
    """
    Don't allow deleting hidden plugins.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.delete(DeleteEnum.PLUGIN, 0)


def test_invisible_delete_download():
    """
    Don't allow deleting hidden downloads.
    """
    with AmmoController() as controller:
        controller.find("nothing")

        with pytest.raises(Warning):
            controller.delete(DeleteEnum.DOWNLOAD, 0)


def test_invisible_move_mod():
    """
    Don't allow moving hidden mods.
    """
    with AmmoController() as controller:
        install_mod(controller, "conflict_1")
        install_mod(controller, "conflict_2")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.move(ComponentEnum.MOD, 0, 1)


def test_invisible_move_plugin():
    """
    Don't allow moving hidden plugins.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "conflict_1")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.move(ComponentEnum.PLUGIN, 0, 1)


def test_invisible_rename_mod():
    """
    Don't allow renaming hidden mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.rename(RenameEnum.MOD, 0, "new_name")


def test_invisible_configure():
    """
    Don't allow configuring invisible mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "mock_relighting_skyrim")

        controller.find("nothing")

        with pytest.raises(Warning):
            controller.configure(0)
