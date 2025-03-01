#!/usr/bin/env python3
import os
import textwrap
from pathlib import Path

from common import (
    AmmoController,
    install_mod,
    extract_mod,
)

import pytest


def test_conflict_resolution():
    """
    Install two mods with the same files. Verify the symlinks
    point back to the mod last in the load order.

    Conflicts for all files are won by a single mod.
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

        # Commit changes
        controller.do_commit()

        # Track our expected mod files to confirm they're different later.
        uniques = []

        def check_links(expected_game_file, expected_mod_file):
            if expected_game_file.is_symlink():
                # Symlink
                assert expected_game_file.readlink() == expected_mod_file

        # Assert that the symlinks point to "mock_conflict_2".
        # Since it was installed last, it will be last
        # in mods load order.
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
            data/mock_plugin.esp
                mock_conflict_1
              * mock_conflict_2
            data/textures/mock_texture.nif
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
