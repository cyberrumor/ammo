#!/usr/bin/env python3
import os
from pathlib import Path

import pytest

from common import AmmoController
from ammo.component import (
    ComponentEnum,
    DeleteEnum,
)


def test_duplicate_plugin():
    """
    Test that installing two mods with the same plugin
    doesn't show more than one plugin in the plugins list.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in ["conflict_1", "conflict_2"]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate(ComponentEnum.MOD, mod_index)
            # Ensure there is only one esp
            assert len(controller.plugins) == 1
            controller.commit()
            assert len(controller.plugins) == 1


def test_conflict_resolution():
    """
    Install two mods with the same files. Verify the symlinks
    point back to the mod last in the load order.

    Conflicts for all files and plugins are won by a single mod.
    """
    files = [
        Path("Data/textures/mock_texture.nif"),
        Path("Data/mock_plugin.esp"),
        Path("file.dll"),
    ]
    with AmmoController() as controller:
        # Install both mods
        for mod in ["conflict_1", "conflict_2"]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate(ComponentEnum.MOD, mod_index)
            controller.commit()

        # Activate the plugin
        controller.activate(ComponentEnum.PLUGIN, 0)

        # Commit changes
        controller.commit()

        # Track our expected mod files to confirm they're different later.
        uniques = []

        def check_links(expected_game_file, expected_mod_file):
            if expected_game_file.is_symlink():
                # Symlink
                assert expected_game_file.readlink() == expected_mod_file
            else:
                # Hardlink
                expected_stat = os.stat(expected_game_file)
                actual_stat = os.stat(expected_mod_file)
                assert expected_stat.st_ino == actual_stat.st_ino

        # Assert that the symlinks point to "conflict_2".
        # Since it was installed last, it will be last
        # in both mods/plugins load order.
        for file in files:
            expected_game_file = controller.game.directory / file
            expected_mod_file = controller.mods[1].location / file
            uniques.append(expected_mod_file)
            check_links(expected_game_file, expected_mod_file)

        # Rearrange the mods
        controller.move(ComponentEnum.MOD, 1, 0)
        controller.commit()

        # Assert that the symlinks point to "conflict_1" now.
        for file in files:
            expected_game_file = controller.game.directory / file
            expected_mod_file = controller.mods[1].location / file

            # Check that a different mod is the conflict winner now.
            assert expected_mod_file not in uniques
            check_links(expected_game_file, expected_mod_file)


def test_conflicting_plugins_disable():
    """
    Install two mods with the same files. Disable the one that is winning the
    conflict for the plugin.

    Test that the plugin isn't removed from the controller's plugins.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in ["conflict_1", "conflict_2"]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate(ComponentEnum.MOD, mod_index)
            controller.commit()

        # plugin is disabled, changes were not / are not committed
        controller.deactivate(ComponentEnum.MOD, 1)
        assert (
            len(controller.plugins) == 1
        ), "Deactivating a mod hid a plugin provided by another mod"

        # plugin is enabled, changes were / are committed
        controller.activate(ComponentEnum.MOD, 1)
        controller.activate(ComponentEnum.PLUGIN, 0)
        controller.commit()
        controller.deactivate(ComponentEnum.MOD, 1)
        controller.commit()
        assert (
            len(controller.plugins) == 1
        ), "Deactivating a mod hid a plugin provided by another mod"

        # ensure the plugin points at mod 0.
        if (plugin := controller.game.data / "mock_plugin.esp").is_symlink():
            # Symlink
            assert plugin.readlink() == (
                (controller.mods[0].location / "Data/mock_plugin.esp")
            ), "Plugin pointed to the wrong mod!"
        else:
            # Hardlink
            plugin_stat = os.stat(plugin)
            expected_stat = os.stat(
                controller.mods[0].location / "Data/mock_plugin.esp"
            )
            assert (
                plugin_stat.st_ino == expected_stat.st_ino
            ), f"Expected inode and actual inode differ! {plugin}"


def test_conflicting_plugins_delete():
    """
    Install two mods with the same files. Delete the one that is winning the
    conflict for the plugin.

    Test that the plugin isn't removed from the controller's plugins.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in ["conflict_1", "conflict_2"]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)
            mod_index = [i.name for i in controller.mods].index(mod)
            controller.activate(ComponentEnum.MOD, mod_index)
            controller.commit()

        # plugin is disabled, changes were not / are not committed
        with pytest.raises(Warning):
            controller.delete(DeleteEnum.MOD, 1)
        assert (
            len(controller.plugins) == 1
        ), "Deleting a mod hid a plugin provided by another mod"
