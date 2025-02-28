#!/usr/bin/env python3
import os
import pytest
from common import (
    AmmoController,
    install_mod,
    extract_mod,
)


def test_move_validation():
    """
    Install several mods, then check various arguments to "move" for validity.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")
        install_mod(controller, "multiple_plugins")

        # Test valid move mod input
        highest = len(controller.mods) - 1
        controller.do_move_mod(0, highest)
        controller.do_move_mod(highest, 0)

        # 'to index' that is too high for move should
        # automatically correct to highest location.
        # Test this on mods.
        highest = len(controller.mods)
        controller.do_move_mod(0, highest)

        # Test invalid 'from index' for mods.
        with pytest.raises(Warning):
            controller.do_move_mod(highest, 0)

        # test non-int first arg for mods
        with pytest.raises(Warning):
            controller.do_move_mod("nan", 0)

        # test non-int second arg for mods
        with pytest.raises(Warning):
            controller.do_move_mod(0, "nan")


def test_activate_validation():
    """
    Install a mod, then check various arguments to "activate" for validity
    """
    with AmmoController() as controller:
        mod_index = extract_mod(controller, "normal_mod")

        # Activate valid mod
        controller.do_activate_mod(mod_index)

        # Activate invalid mod
        with pytest.raises(Warning):
            controller.do_activate_mod(1000)


def test_deactivate_validation():
    """
    Install a mod, then check various arguments to "deactivate" for validity
    """
    with AmmoController() as controller:
        mod_index = install_mod(controller, "normal_mod")

        # valid deactivate mod
        controller.do_deactivate_mod(mod_index)

        # invalid deactivate mod
        with pytest.raises(Warning):
            controller.do_deactivate_mod(1000)

        # non-int
        with pytest.raises(Warning):
            controller.do_deactivate_mod("nan")


def test_install_validation():
    """
    Attempt to install a valid and invalid index.
    """
    with AmmoController() as controller:
        controller.do_install(0)

        with pytest.raises(Warning):
            controller.do_install(1000)


def test_delete_validation():
    """
    Delete a valid and invalid mod and download
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        # delete mod out of range
        with pytest.raises(Warning):
            controller.do_delete_mod(1000)

        # delete mod in range
        controller.do_delete_mod(0)

        # delete download out of range
        with pytest.raises(Warning):
            controller.do_delete_download(1000)

        # generate an expendable download file, delete
        # download in range.
        with open(os.path.join(controller.downloads_dir, "temp_download.7z"), "w") as f:
            f.write("")

        controller.do_refresh()

        download_index = [i.name for i in controller.downloads].index(
            "temp_download.7z"
        )
        controller.do_delete_download(download_index)

        # Delete non-int download
        with pytest.raises(Warning):
            controller.do_delete_download("nan")

        # Delete non-int mod
        with pytest.raises(Warning):
            controller.do_delete_mod("nan")


def test_no_components_validation():
    """
    In the absence of any mods or downloads,
    attempt each operation type (besides install/delete download).
    """
    with AmmoController() as controller:
        # attempt to move mod
        with pytest.raises(Warning):
            controller.do_move_mod(0, 1)

        # attempt to delete mod
        with pytest.raises(Warning):
            controller.do_delete_mod(0)

        # attempt to activate mod
        with pytest.raises(Warning):
            controller.do_activate_mod(0)

        # attempt to deactivate mod
        with pytest.raises(Warning):
            controller.do_deactivate_mod(0)


def test_no_install_twice():
    """
    Attempting to install a mod that is already installed isn't supported.
    Explicitly test that this is not allowed.
    """
    with AmmoController() as controller:
        install_mod(controller, "normal_mod")

        with pytest.raises(Warning):
            install_mod(controller, "normal_mod")


def test_invisible_install():
    """
    Don't allow installing hidden downloads.
    """
    with AmmoController() as controller:
        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_install(0)


def test_install_nan():
    """
    Don't allow installing non-ints
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_install("nan")


def test_invisible_delete_mod():
    """
    Don't allow deleting hidden mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")

        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_delete_mod(0)


def test_invisible_delete_download():
    """
    Don't allow deleting hidden downloads.
    """
    with AmmoController() as controller:
        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_delete_download(0)


def test_invisible_move_mod():
    """
    Don't allow moving hidden mods.
    """
    with AmmoController() as controller:
        install_mod(controller, "conflict_1")
        install_mod(controller, "conflict_2")

        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_move_mod(0, 1)


def test_invisible_rename_mod():
    """
    Don't allow renaming hidden mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "normal_mod")

        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_rename_mod(0, "new_name")


def test_invisible_configure():
    """
    Don't allow configuring invisible mods.
    """
    with AmmoController() as controller:
        extract_mod(controller, "mock_relighting_skyrim")

        controller.do_find("nothing")

        with pytest.raises(Warning):
            controller.do_configure(0)


def test_configure_high_index():
    """
    Don't crash when configuring an index out of range.
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_configure(0)


def test_configure_nan():
    """
    Don't crash when configuring nan
    """
    with AmmoController() as controller:
        with pytest.raises(Warning):
            controller.do_configure("nan")


def test_collisions():
    """
    Don't crash if collisions gets bad arguments
    """
    with AmmoController() as controller:
        # int that's out of range
        with pytest.raises(Warning):
            controller.do_collisions(0)

        # non-int
        with pytest.raises(Warning):
            controller.do_collisions("nan")
