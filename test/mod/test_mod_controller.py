#!/usr/bin/env python3
import os
import shutil
import textwrap

import pytest

from mod_common import (
    AmmoController,
    extract_mod,
    install_everything,
    install_mod,
)


def test_controller_first_launch():
    """
    Sanity check the ammo_controller fixture, that it creates
    the game directory and properly removes it.
    """
    with AmmoController() as controller:
        game_dir = controller.game.directory
        assert os.path.exists(game_dir), (
            f"game_dir {game_dir} did not exist after the controller started."
        )

        downloads_dir = controller.downloads_dir
        assert os.path.exists(downloads_dir), (
            f"downloads_dir {downloads_dir} did not exist after the controller started."
        )

        conf_dir = os.path.split(controller.game.ammo_conf)[0]
        assert os.path.exists(conf_dir), (
            f"ammo_dir {conf_dir} did not exist after the controller started."
        )

    assert not os.path.exists(game_dir), (
        f"game_dir {game_dir} was not removed after context manager closed"
    )

    assert os.path.exists(downloads_dir), (
        f"downloads_dir {downloads_dir} was deleted after context manager closed.\
        It would be a good time to `git checkout Downloads`"
    )

    assert not os.path.exists(conf_dir), (
        f"ammo_dir {conf_dir} existed after the context manager closed."
    )


def test_controller_subsequent_launch(mock_has_extra_folder):
    """
    Ensure ammo behaves correctly when launched against a game
    that already has mods installed, Plugins.txt populated with
    a non-default order, etc.
    """
    with AmmoController() as first_launch:
        install_everything(first_launch)

        # change some config to ensure it's not just alphabetic
        first_launch.move_mod(2, 0)
        first_launch.deactivate_mod(1)
        first_launch.do_commit()

        mods = [(i.name, i.location, i.enabled) for i in first_launch.mods]
        downloads = [(i.name, i.location) for i in first_launch.downloads]

        # Launch the second instance of ammo against this configuration.
        with AmmoController() as controller:
            # check mods are the same
            assert [(i.name, i.location, i.enabled) for i in controller.mods] == mods, (
                "Mods didn't load correctly on subsequent session"
            )

            # check downloads are the same
            assert [(i.name, i.location) for i in controller.downloads] == downloads, (
                "Downloads didn't load correctly on subsequent session"
            )


def test_controller_move(mock_has_extra_folder):
    """
    Test that moving a mod to a new position causes the
    components between the old location and the new location to collapse
    (take out at old location, insert at new location), rather than
    causing the old location and new location components to merely swap.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "mock_conflict_1")
        install_mod(controller, "mock_conflict_2")

        assert controller.mods[0].name == "normal_mod"
        assert controller.mods[1].name == "mock_conflict_1"
        assert controller.mods[2].name == "mock_conflict_2"

        controller.move_mod(1, 3)  # index larger than list should resolve to len()
        assert controller.mods[0].name == "normal_mod"
        assert controller.mods[1].name == "mock_conflict_2"
        assert controller.mods[2].name == "mock_conflict_1"


def test_controller_missing_mod(mock_has_extra_folder):
    """
    Test that a mod which is specified in ammo.conf but can't be
    found (because it was deleted from ammo's mod dir) isn't added
    to mods.
    """
    with pytest.raises(AssertionError):
        with AmmoController() as first_launch:
            index = install_mod(first_launch, "normal_mod")
            mod = first_launch.mods[index]
            shutil.rmtree(mod.location)

            with AmmoController() as controller:
                assert len(controller.mods) == 0


def test_no_delete_all_if_mod_active(mock_has_extra_folder):
    """
    It's not the first time I've done this on accident, but
    it will be the last. Test that deleting all mods fails if
    any visible mod is still enabled. In other words, deleting
    all mods is only allowed if all visible mods are inactive.
    """
    with AmmoController() as controller:
        install_mod(controller, "mock_conflict_1")
        extract_mod(controller, "mock_conflict_2")

        expected = "You must deactivate all visible components of that type before deleting them with all."

        with pytest.raises(Warning) as warning:
            controller.delete_mod("all")
            assert warning.value.args == (expected,)


def test_mod_controller_str(mock_has_extra_folder):
    """
    Test that the ModController looks the way we expect.
    """
    expected = textwrap.dedent(
        """\
         index | Download
        -------|---------
        [0]     aaa.7z
        [1]     duplicate_filenames.7z
        [2]     edit_scripts.7z
        [3]     esl.7z
        [4]     esm.7z
        [5]     missing_data.7z
        [6]     mock_base_object_swapper.7z
        [7]     mock_conflict_1.7z
        [8]     mock_conflict_2.7z
        [9]     mock_embers_xd.7z
        [10]    mock_engine_fixes_part_1.7z
        [11]    mock_engine_fixes_part_2.7z
        [12]    mock_evlas_underside.7z
        [13]    mock_immersive_armors.7z
        [14]    mock_placed_light.7z
        [15]    mock_realistic_ragdolls.7z
        [16]    mock_relighting_skyrim.7z
        [17]    mock_script_extender.7z
        [18]    mock_skyui.7z
        [19]    mult_plugins_same_name.7z
        [20]    multiple_plugins.7z
        [21]    no_data_folder_dll.7z
        [22]    no_data_folder_plugin.7z
        [23]    normal_mod.7z
        [24]    pak_mods.7z
        [25]    pak_no_dir.7z
        [26]    pak_root.7z
        [27]    plugin_wrong_spot.7z
        [28]    zzz.7z

         index | Active | Mod name
        -------|--------|------------
        [0]     [True]    normal_mod
        [1]     [False]   mock_conflict_1
        """
    )

    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        extract_mod(controller, "mock_conflict_1")

        assert str(controller) == expected
