#!/usr/bin/env python3
import os
from common import AmmoController, install_everything


def test_controller_fixture():
    """
    Sanity check the ammo_controller fixture, that it creates
    the game directory and properly removes it.
    """
    with AmmoController() as controller:
        assert os.path.exists(
            controller.game_dir
        ), "game_dir did not exist after the controller started."
        assert os.path.exists(
            controller.data_dir
        ), "data_dir did not exist after the controller started."
        assert os.path.exists(
            controller.downloads_dir
        ), "downloads_dir did not exist after the controller started."
        assert os.path.exists(
            os.path.split(controller.conf)[0]
        ), "ammo_dir did not exist after the controller started."


def test_controller_on_preconfigured_game():
    """
    Ensure ammo behaves correctly when launched against a game
    that already has mods installed, Plugins.txt populated with
    a non-default order, etc.
    """
    with AmmoController() as first_launch:
        install_everything(first_launch)

        # change some config to ensure it's not just alphabetic
        first_launch.move("plugin", 0, 2)
        first_launch.move("mod", 2, 0)
        first_launch.commit()

        mods = [i.name for i in first_launch.mods]
        downloads = [i.name for i in first_launch.downloads]
        plugins = [i.name for i in first_launch.plugins]

        # Launch the second instance of ammo against this configuration.
        with AmmoController() as controller:
            # check mods are the same
            assert (
                [i.name for i in controller.mods] == mods
            ), "Mods didn't load correctly on subsequent session"

            # check downloads are the same
            assert (
                [i.name for i in controller.downloads] == downloads
            ), "Downloads didn't load correctly on subsequent session"

            # check plugins are the same
            assert (
                [i.name for i in controller.plugins] == plugins
            ), "Plugins didn't load correctly on subsequent session"
