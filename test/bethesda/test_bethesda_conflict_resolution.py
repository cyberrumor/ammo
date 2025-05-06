#!/usr/bin/env python3
import os
import textwrap
from pathlib import Path

from bethesda_common import (
    AmmoController,
    install_mod,
    extract_mod,
)

import pytest


def test_duplicate_plugin():
    """
    Test that installing two mods with the same plugin
    doesn't show more than one plugin in the plugins list.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.do_activate_mod(mod_index)
            # Ensure there is only one esp
            assert len(controller.plugins) == 1
            controller.do_commit()
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
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.do_activate_mod(mod_index)
            controller.do_commit()

        # Activate the plugin
        controller.do_activate_plugin(0)

        # Commit changes
        controller.do_commit()

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

        # Assert that the symlinks point to "mock_conflict_2".
        # Since it was installed last, it will be last
        # in both mods/plugins load order.
        for file in files:
            expected_game_file = controller.game.directory / file
            expected_mod_file = controller.mods[1].location / file
            uniques.append(expected_mod_file)
            check_links(expected_game_file, expected_mod_file)

        # Rearrange the mods
        controller.do_move_mod(1, 0)
        controller.do_commit()

        # Assert that the symlinks point to "mock_conflict_1" now.
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
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)

            mod_index = [i.name for i in controller.mods].index(mod)

            controller.do_activate_mod(mod_index)
            controller.do_commit()

        # plugin is disabled, changes were not / are not committed
        controller.do_deactivate_mod(1)
        assert len(controller.plugins) == 1, (
            "Deactivating a mod hid a plugin provided by another mod"
        )

        # plugin is enabled, changes were / are committed
        controller.do_activate_mod(1)
        controller.do_activate_plugin(0)
        controller.do_commit()
        controller.do_deactivate_mod(1)
        controller.do_commit()
        assert len(controller.plugins) == 1, (
            "Deactivating a mod hid a plugin provided by another mod"
        )

        # ensure the plugin points at mod 0.
        if (plugin := controller.game.data / "mock_plugin.esp").is_symlink():
            # Symlink
            assert plugin.readlink() == (
                controller.mods[0].location / "Data/mock_plugin.esp"
            ), "Plugin pointed to the wrong mod!"
        else:
            # Hardlink
            plugin_stat = os.stat(plugin)
            expected_stat = os.stat(
                controller.mods[0].location / "Data/mock_plugin.esp"
            )
            assert plugin_stat.st_ino == expected_stat.st_ino, (
                f"Expected inode and actual inode differ! {plugin}"
            )


def test_conflicting_plugins_delete():
    """
    Install two mods with the same files. Delete the one that is winning the
    conflict for the plugin.

    Test that the plugin isn't removed from the controller's plugins.
    """
    with AmmoController() as controller:
        # Install both mods
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)
            mod_index = [i.name for i in controller.mods].index(mod)
            controller.do_activate_mod(mod_index)
            controller.do_commit()

        controller.do_delete_mod(1)
        assert len(controller.plugins) == 1, (
            "Deleting a mod hid a plugin provided by another mod"
        )


def test_conflicting_plugins_delete_plugin():
    """
    Install two mods with the same files. Delete a plugin provided
    by both mods. Expect the plugin to be deleted from both mods.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)
            mod_index = [i.name for i in controller.mods].index(mod)
            controller.do_activate_mod(mod_index)
            controller.do_commit()

        controller.do_delete_plugin(0)

        assert len(controller.plugins) == 0, (
            "A plugin provided by multiple enabled mods wasn't deleted."
        )

        controller.do_deactivate_mod("all")
        controller.do_activate_mod("all")

        assert len(controller.plugins) == 0, (
            "A plugin provided by multiple mods came back from the grave!"
        )


def test_conflicting_plugins_mult_delete_plugin():
    """
    Install two mods with the same plugin. One of those mods has an extra
    plugin by the same name but in somewhere besides Data. Expect the plugin
    to be deleted from both mods, but the plugin that was in the wrong spot
    is not removed.
    """
    with AmmoController() as controller:
        for mod in ["plugin_wrong_spot", "mult_plugins_same_name"]:
            install_mod(controller, mod)

        controller.do_delete_plugin(0)
        files = (
            src
            for src, dest in controller.mods[
                [i.name for i in controller.mods].index("plugin_wrong_spot")
            ].files
        )
        file = controller.game.ammo_mods_dir / "plugin_wrong_spot/Data/test/plugin.esp"
        # Check that we didn't delete a plugin that wasn't in Data
        assert file in files

        files = [
            src
            for src, dest in controller.mods[
                [i.name for i in controller.mods].index("mult_plugins_same_name")
            ].files
        ]
        file = controller.game.ammo_mods_dir / "mult_plugins_same_name/Data/plugin.esp"
        # Check that we deleted what we intended to
        assert file not in files

        file = (
            controller.game.ammo_mods_dir
            / "mult_plugins_same_name/Data/test/plugin.esp"
        )
        # Check that we didn't delete a plugin that wasn't in Data
        assert file in files


def test_conflicting_mods_have_conflict_flag_after_install():
    """
    Test that only conflicting mods have mod.conflict set to True
    after install.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            install_mod(controller, mod)

        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_1")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_2")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("normal_mod")
            ].conflict
            is False
        )


def test_conflicting_mods_have_conflict_flag_after_move():
    """
    Test that only conflicting mods have mod.conflict set to True
    after move.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            install_mod(controller, mod)

        controller.do_move_mod(2, 0)

        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_1")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_2")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("normal_mod")
            ].conflict
            is False
        )


def test_conflicting_mods_have_conflict_flag_after_actviate():
    """
    Test that only conflicting mods have mod.conflict set to True
    after activate.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            extract_mod(controller, mod)

        controller.do_activate_mod(0)
        controller.do_activate_mod(1)
        controller.do_activate_mod(2)

        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_1")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_2")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("normal_mod")
            ].conflict
            is False
        )


def test_conflicting_mods_have_conflict_flag_after_deactivate():
    """
    Test that only conflicting mods have mod.conflict set to True
    after deactivate.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            install_mod(controller, mod)

        controller.do_deactivate_mod(2)

        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_1")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("mock_conflict_2")
            ].conflict
            is True
        )
        assert (
            controller.mods[
                [i.name for i in controller.mods].index("normal_mod")
            ].conflict
            is False
        )


def test_conflicting_mods_only_conflict_when_activated():
    """
    Test that only activated mods are considered when determining conflicts.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            extract_mod(controller, mod)

        assert controller.mods[0].conflict is False
        assert controller.mods[1].conflict is False

        controller.do_activate_mod(0)
        assert controller.mods[0].conflict is False
        assert controller.mods[1].conflict is False

        controller.do_activate_mod(1)
        assert controller.mods[0].conflict is True
        assert controller.mods[1].conflict is True


def test_conflicting_mods_conflict_after_rename():
    """
    Test that conflicting mods still conflict after rename
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2"]:
            install_mod(controller, mod)

        controller.do_rename_mod(0, "new_name")

        assert controller.mods[0].conflict is True
        assert controller.mods[1].conflict is True


def test_collisions():
    """
    Test that the 'collisions' command indicates
    all and only conflicting files, indicating the
    conflict winning mod with an "*".
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            install_mod(controller, mod)

        mock_conflict_1 = [i.name for i in controller.mods].index("mock_conflict_1")
        mock_conflict_2 = [i.name for i in controller.mods].index("mock_conflict_2")
        normal_mod = [i.name for i in controller.mods].index("normal_mod")

        expected = textwrap.dedent(
            """\
            file.dll
                mock_conflict_1
              * mock_conflict_2
            Data/mock_plugin.esp
                mock_conflict_1
              * mock_conflict_2
            Data/textures/mock_texture.nif
                mock_conflict_1
              * mock_conflict_2
        """
        )

        with pytest.raises(Warning) as warning:
            controller.do_collisions(mock_conflict_1)
        assert warning.value.args == (expected,)

        with pytest.raises(Warning) as warning:
            controller.do_collisions(mock_conflict_2)
        assert warning.value.args == (expected,)

        with pytest.raises(Warning) as warning:
            controller.do_collisions(normal_mod)
        assert warning.value.args == ("No conflicts.",)


def test_obsolete_init():
    """
    Test that mods are properly marked as obsolete on move/enable/disable.
    """
    with AmmoController() as controller:
        for mod in ["mock_conflict_1", "mock_conflict_2", "normal_mod"]:
            install_mod(controller, mod)

        mock_conflict_1 = [i.name for i in controller.mods].index("mock_conflict_1")
        mock_conflict_2 = [i.name for i in controller.mods].index("mock_conflict_2")
        normal_mod = [i.name for i in controller.mods].index("normal_mod")

        assert controller.mods[mock_conflict_1].obsolete is True
        assert controller.mods[mock_conflict_2].obsolete is False
        assert controller.mods[normal_mod].obsolete is False

        # perform a move
        controller.do_move_mod(mock_conflict_1, mock_conflict_2)
        # fix indices
        mock_conflict_1, mock_conflict_2 = mock_conflict_2, mock_conflict_1

        assert controller.mods[mock_conflict_2].obsolete is True
        assert controller.mods[mock_conflict_1].obsolete is False
        assert controller.mods[normal_mod].obsolete is False

        # Perform a deactivate
        controller.do_deactivate_mod(mock_conflict_1)
        assert controller.mods[mock_conflict_2].obsolete is False
        assert controller.mods[normal_mod].obsolete is False
