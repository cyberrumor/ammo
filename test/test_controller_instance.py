#!/usr/bin/env python3
import os
from common import AmmoController, install_everything


def test_controller_first_launch():
    """
    Sanity check the ammo_controller fixture, that it creates
    the game directory and properly removes it.
    """
    with AmmoController() as controller:
        game_dir = controller.game.directory
        assert os.path.exists(
            game_dir
        ), f"game_dir {game_dir} did not exist after the controller started."

        data_dir = controller.game.data
        assert os.path.exists(
            data_dir
        ), f"data_dir {data_dir} did not exist after the controller started."

        downloads_dir = controller.downloads_dir
        assert os.path.exists(
            downloads_dir
        ), f"downloads_dir {downloads_dir} did not exist after the controller started."

        conf_dir = os.path.split(controller.game.ammo_conf)[0]
        assert os.path.exists(
            conf_dir
        ), f"ammo_dir {conf_dir} did not exist after the controller started."

    assert not os.path.exists(
        game_dir
    ), f"game_dir {game_dir} was not removed after context manager closed"

    assert not os.path.exists(
        data_dir
    ), f"data dir {data_dir} was not removed after context manager closed"

    assert os.path.exists(
        downloads_dir
    ), f"downloads_dir {downloads_dir} was deleted after context manager closed.\
        It would be a good time to `git checkout Downloads`"

    assert not os.path.exists(
        conf_dir
    ), f"ammo_dir {conf_dir} existed after the context manager closed."


def test_controller_subsequent_launch():
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
            assert [
                i.name for i in controller.mods
            ] == mods, "Mods didn't load correctly on subsequent session"

            # check downloads are the same
            assert [
                i.name for i in controller.downloads
            ] == downloads, "Downloads didn't load correctly on subsequent session"

            # check plugins are the same
            assert [
                i.name for i in controller.plugins
            ] == plugins, "Plugins didn't load correctly on subsequent session"
