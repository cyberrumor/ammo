#!/usr/bin/env python3
import os
from common import AmmoController


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
