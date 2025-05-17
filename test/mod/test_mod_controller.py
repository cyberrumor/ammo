#!/usr/bin/env python3
import os
import shutil

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
        first_launch.do_move_mod(2, 0)
        first_launch.do_deactivate_mod(1)
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

        controller.do_move_mod(1, 3)  # index larger than list should resolve to len()
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
            controller.do_delete_mod("all")
            assert warning.value.args == (expected,)
