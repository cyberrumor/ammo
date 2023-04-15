#!/usr/bin/env python3
import os
from common import AmmoController

MOD_1 = "mock_conflict_1.7z"
MOD_2 = "mock_conflict_2.7z"

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
            mod_index_download = [i.name for i in controller.downloads].index(mod)
            controller.install(mod_index_download)

            mod_name = mod.strip(".7z")
            mod_index = [i.name for i in controller.mods].index(mod_name)

            controller.activate("mod", mod_index)
            # Ensure we have only 1 esp.
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
            mod_index_download = [i.name for i in controller.downloads].index(mod)
            controller.install(mod_index_download)

            mod_name = mod.strip(".7z")
            mod_index = [i.name for i in controller.mods].index(mod_name)

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
