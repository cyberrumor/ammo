#!/usr/bin/env python3
import os
from common import AmmoController

MOD_1 = "conflict_1"
MOD_2 = "conflict_2"

FILES = [
    "Data/textures/mock_texture.nif",
    "Data/mock_plugin.esp",
    "file.dll",
]


def test_duplicate_plugin():
    """
    Test that installing two mods with the same plugin
    doesn't show more than one plugin in the plugins list.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in [MOD_1, MOD_2]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate("mod", mod_index)
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
    with AmmoController() as controller:
        # Install both mods
        for mod in [MOD_1, MOD_2]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate("mod", mod_index)
            controller.commit()

        # Activate the plugin
        controller.activate("plugin", 0)

        # Commit changes
        controller.commit()

        # Track our expected mod files to confirm they're different later.
        uniques = []

        # Assert that the symlinks point to MOD_2.
        # Since it was installed last, it will be last
        # in both mods/plugins load order.
        for file in FILES:
            expected_game_file = os.path.join(controller.game_dir, file)
            expected_mod_file = os.path.join(controller.mods[1].location, file)
            uniques.append(expected_mod_file)

            assert os.readlink(expected_game_file) == expected_mod_file

        # Rearrange the mods
        controller.move("mod", 1, 0)
        controller.commit()

        # Assert that the symlinks point to MOD_1 now.
        for file in FILES:
            expected_game_file = os.path.join(controller.game_dir, file)
            expected_mod_file = os.path.join(controller.mods[1].location, file)

            # Check that a different mod is the conflict winner now.
            assert expected_mod_file not in uniques

            assert os.readlink(expected_game_file) == expected_mod_file


def test_conflicting_plugins_disable():
    """
    Install two mods with the same files. Disable the one that is winning the
    conflict for the plugin.

    Test that the plugin isn't removed from the controller's plugins.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in [MOD_1, MOD_2]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.activate("mod", mod_index)
            controller.commit()

        # plugin is disabled, changes were not / are not committed
        controller.deactivate("mod", 1)
        assert (
            len(controller.plugins) == 1
        ), "Deactivating a mod hid a plugin provided by another mod"

        # plugin is enabled, changes were / are committed
        controller.activate("mod", 1)
        controller.activate("plugin", 0)
        controller.commit()
        controller.deactivate("mod", 1)
        controller.commit()
        assert (
            len(controller.plugins) == 1
        ), "Deactivating a mod hid a plugin provided by another mod"

        # ensure the plugin points at mod 0
        assert os.readlink(
            os.path.join(controller.data_dir, "mock_plugin.esp")
        ) == os.path.join(
            controller.mods[0].location, "Data/mock_plugin.esp"
        ), "Plugin pointed to the wrong mod!"


def test_conflicting_plugins_delete():
    """
    Install two mods with the same files. Delete the one that is winning the
    conflict for the plugin.

    Test that the plugin isn't removed from the controller's plugins.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in [MOD_1, MOD_2]:
            mod_index_download = [i.name for i in controller.downloads].index(
                mod + ".7z"
            )
            controller.install(mod_index_download)
            mod_index = [i.name for i in controller.mods].index(mod)
            controller.activate("mod", mod_index)
            controller.commit()

        # plugin is disabled, changes were not / are not committed
        controller.delete("mod", 1)
        assert (
            len(controller.plugins) == 1
        ), "Deleting a mod hid a plugin provided by another mod"
